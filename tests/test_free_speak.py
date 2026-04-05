import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pawnai_bob.callbacks import Callbacks
from pawnai_bob.commands.room_config_commands import RoomConfigCommands
from pawnai_bob.commands.system_commands import SystemCommands
from pawnai_bob.processors.audio_processor import AudioProcessor
from pawnai_bob.room import Room


class CallbacksFreeSpeakTests(unittest.IsolatedAsyncioTestCase):
    async def test_prefixed_text_keeps_system_command_routing(self):
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(body="!bob help", sender="@user:example.com")

        with patch(
            "pawnai_bob.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_bob.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_bob.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[]),
        ):
            callbacks = Callbacks()
            callbacks.room_listener.store_message_text = AsyncMock()
            callbacks.system_commands.process = AsyncMock(return_value=True)
            callbacks.conversation_commands.process = AsyncMock()

            await callbacks.message(matrix_room, event)

        callbacks.room_listener.store_message_text.assert_not_called()
        callbacks.system_commands.process.assert_awaited_once_with(
            "help", matrix_room, event
        )
        callbacks.conversation_commands.process.assert_not_called()

    async def test_unprefixed_text_is_stored_only_when_free_speak_disabled(self):
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(body="hello there", sender="@user:example.com")

        with patch(
            "pawnai_bob.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_bob.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_bob.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[]),
        ), patch(
            "pawnai_bob.callbacks.room",
            return_value=SimpleNamespace(get_free_speak=lambda _: False),
        ):
            callbacks = Callbacks()
            callbacks.room_listener.store_message_text = AsyncMock()
            callbacks.conversation_commands.process = AsyncMock()

            await callbacks.message(matrix_room, event)

        callbacks.room_listener.store_message_text.assert_awaited_once_with(
            matrix_room, event
        )
        callbacks.conversation_commands.process.assert_not_called()

    async def test_unprefixed_text_is_routed_to_chat_when_free_speak_enabled(self):
        reply_event = SimpleNamespace()
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(body="ignored in reply mode", sender="@user:example.com")

        with patch(
            "pawnai_bob.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_bob.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_bob.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[reply_event]),
        ), patch(
            "pawnai_bob.callbacks.get_reply_body",
            return_value="tell me a joke",
        ), patch(
            "pawnai_bob.callbacks.room",
            return_value=SimpleNamespace(get_free_speak=lambda _: True),
        ):
            callbacks = Callbacks()
            callbacks.room_listener.store_message_text = AsyncMock()
            callbacks.conversation_commands.process = AsyncMock(return_value="ok")

            await callbacks.message(matrix_room, event)

        callbacks.room_listener.store_message_text.assert_awaited_once_with(
            matrix_room, event
        )
        callbacks.conversation_commands.process.assert_awaited_once_with(
            "tell me a joke", matrix_room, event, [reply_event]
        )


class AudioProcessorFreeSpeakTests(unittest.IsolatedAsyncioTestCase):
    async def test_unprefixed_audio_transcript_is_ignored_when_free_speak_disabled(self):
        matrix_room = SimpleNamespace()
        event = SimpleNamespace()

        with patch(
            "pawnai_bob.processors.audio_processor.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_bob.processors.audio_processor.room",
            return_value=SimpleNamespace(get_free_speak=lambda _: False),
        ):
            processor = AudioProcessor()
            processor._system_commands.process = AsyncMock()
            processor._conversation_commands.process = AsyncMock()

            await processor._route_transcript(matrix_room, event, "hello there")

        processor._system_commands.process.assert_not_called()
        processor._conversation_commands.process.assert_not_called()

    async def test_unprefixed_audio_transcript_is_routed_to_chat_when_enabled(self):
        matrix_room = SimpleNamespace()
        event = SimpleNamespace()

        with patch(
            "pawnai_bob.processors.audio_processor.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_bob.processors.audio_processor.room",
            return_value=SimpleNamespace(get_free_speak=lambda _: True),
        ):
            processor = AudioProcessor()
            processor._system_commands.process = AsyncMock()
            processor._conversation_commands.process = AsyncMock()

            await processor._route_transcript(matrix_room, event, "hello there")

        processor._system_commands.process.assert_not_called()
        processor._conversation_commands.process.assert_awaited_once_with(
            "hello there", matrix_room, event, []
        )

    async def test_prefixed_audio_transcript_keeps_command_routing(self):
        matrix_room = SimpleNamespace()
        event = SimpleNamespace()

        with patch(
            "pawnai_bob.processors.audio_processor.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_bob.processors.audio_processor.room",
            return_value=SimpleNamespace(get_free_speak=lambda _: True),
        ):
            processor = AudioProcessor()
            processor._system_commands.process = AsyncMock(return_value=True)
            processor._conversation_commands.process = AsyncMock()

            await processor._route_transcript(matrix_room, event, "bob help")

        processor._system_commands.process.assert_awaited_once_with(
            "help", matrix_room, event
        )
        processor._conversation_commands.process.assert_not_called()


class RoomFreeSpeakPersistenceTests(unittest.TestCase):
    def test_default_configuration_disables_free_speak(self):
        manager = Room({}, None)

        self.assertFalse(manager._create_default_configuration()["free_speak"])

    def test_save_configuration_persists_free_speak_flag(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")

        class FakeSession:
            def __init__(self):
                self.added = []
                self.committed = False

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def scalar(self, _statement):
                return None

            def add(self, obj):
                self.added.append(obj)

            def commit(self):
                self.committed = True

        class FakeStore:
            def __init__(self, session):
                self.session = session

            def get_session(self):
                return self.session

        session = FakeSession()
        manager = Room({}, FakeStore(session))
        manager.configuration[matrix_room.room_id] = {
            "client": None,
            "expert_id": -1,
            "expert_name": "",
            "echo": True,
            "free_speak": True,
            "users": {},
        }

        manager.save_configuration(matrix_room)

        self.assertTrue(session.committed)
        self.assertEqual(len(session.added), 1)
        self.assertIsNone(session.added[0].expert_id)
        self.assertTrue(json.loads(session.added[0].configuration)["free_speak"])

    def test_load_configuration_maps_null_expert_to_unset(self):
        manager = Room({}, None)
        conf = manager._build_configuration(
            expert_id=None,
            expert_name="",
            json_config={"echo": True, "free_speak": False, "users": {}},
        )

        self.assertEqual(conf["expert_id"], -1)


class RoomCommandHelpTests(unittest.IsolatedAsyncioTestCase):
    async def test_incomplete_free_speak_set_shows_room_help(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(sender="@admin:example.com")
        send_text = AsyncMock()

        with patch(
            "pawnai_bob.commands.system_commands.send_text_to_room",
            new=send_text,
        ), patch(
            "pawnai_bob.utils.chat.send_text_to_room",
            new=send_text,
        ), patch(
            "pawnai_bob.client",
            return_value=SimpleNamespace(),
        ), patch(
            "pawnai_bob.config",
            return_value={"matrix.power_users": ["@admin:example.com"]},
        ):
            commands = SystemCommands()
            commands._room_commands = RoomConfigCommands()

            handled = await commands.process(" room set free_speak", matrix_room, event)

        self.assertTrue(handled)
        send_text.assert_awaited_once()
        help_text = send_text.await_args.args[2]
        self.assertIn("room set free_speak (on|off)", help_text)


if __name__ == "__main__":
    unittest.main()
