import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from pawnai_matrix.callbacks import Callbacks
from pawnai_matrix.commands.room_config_commands import RoomConfigCommands
from pawnai_matrix.commands.session_commands import SessionCommands
from pawnai_matrix.commands.system_commands import SystemCommands
from pawnai_matrix.processors.audio_processor import AudioProcessor
from pawnai_matrix.room import Room


class CallbacksFreeSpeakTests(unittest.IsolatedAsyncioTestCase):
    async def test_prefixed_text_keeps_system_command_routing(self):
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(body="!bob help", sender="@user:example.com")

        with patch(
            "pawnai_matrix.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_matrix.callbacks.get_related_reply_to_events",
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
            "pawnai_matrix.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_matrix.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[]),
        ), patch(
            "pawnai_matrix.callbacks.room",
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
            "pawnai_matrix.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_matrix.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[reply_event]),
        ), patch(
            "pawnai_matrix.callbacks.get_reply_body",
            return_value="tell me a joke",
        ), patch(
            "pawnai_matrix.callbacks.room",
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

    async def test_unprefixed_backslash_reset_routes_to_session_reset(self):
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(body=r"\reset", sender="@user:example.com")

        with patch(
            "pawnai_matrix.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_matrix.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[]),
        ):
            callbacks = Callbacks()
            callbacks.room_listener.store_message_text = AsyncMock()
            callbacks.system_commands.process = AsyncMock(return_value=True)
            callbacks.conversation_commands.process = AsyncMock()

            await callbacks.message(matrix_room, event)

        callbacks.system_commands.process.assert_awaited_once_with(
            "session reset", matrix_room, event
        )
        callbacks.room_listener.store_message_text.assert_not_called()
        callbacks.conversation_commands.process.assert_not_called()

    async def test_edited_message_with_new_content_routes_command(self):
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(
            body="* typo",
            sender="@user:example.com",
            source={
                "content": {
                    "m.relates_to": {"rel_type": "m.replace"},
                    "m.new_content": {"body": "!bob help"},
                }
            },
        )

        with patch(
            "pawnai_matrix.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_matrix.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[]),
        ):
            callbacks = Callbacks()
            callbacks.room_listener.store_message_text = AsyncMock()
            callbacks.system_commands.process = AsyncMock(return_value=True)
            callbacks.conversation_commands.process = AsyncMock()

            await callbacks.message(matrix_room, event)

        callbacks.system_commands.process.assert_awaited_once_with(
            "help", matrix_room, event
        )
        callbacks.room_listener.store_message_text.assert_not_called()
        callbacks.conversation_commands.process.assert_not_called()

    async def test_edited_message_fallback_strips_asterisk_for_command(self):
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(
            body="* !bob help",
            sender="@user:example.com",
            source={"content": {"m.relates_to": {"rel_type": "m.replace"}}},
        )

        with patch(
            "pawnai_matrix.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_matrix.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[]),
        ):
            callbacks = Callbacks()
            callbacks.room_listener.store_message_text = AsyncMock()
            callbacks.system_commands.process = AsyncMock(return_value=True)
            callbacks.conversation_commands.process = AsyncMock()

            await callbacks.message(matrix_room, event)

        callbacks.system_commands.process.assert_awaited_once_with(
            "help", matrix_room, event
        )
        callbacks.room_listener.store_message_text.assert_not_called()
        callbacks.conversation_commands.process.assert_not_called()

    async def test_edited_non_command_routes_to_chat_when_free_speak_enabled(self):
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(
            body="* hello there",
            sender="@user:example.com",
            source={"content": {"m.relates_to": {"rel_type": "m.replace"}}},
        )

        with patch(
            "pawnai_matrix.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_matrix.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[]),
        ), patch(
            "pawnai_matrix.callbacks.room",
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
            "hello there", matrix_room, event, []
        )

    async def test_edited_non_command_stores_normalized_text_when_free_speak_disabled(self):
        matrix_room = SimpleNamespace(
            display_name="Test Room",
            user_name=lambda sender: sender,
        )
        event = SimpleNamespace(
            body="* hello there",
            sender="@user:example.com",
            source={"content": {"m.relates_to": {"rel_type": "m.replace"}}},
        )

        with patch(
            "pawnai_matrix.callbacks.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.callbacks.client",
            return_value=SimpleNamespace(user="@bob:example.com"),
        ), patch(
            "pawnai_matrix.callbacks.get_related_reply_to_events",
            new=AsyncMock(return_value=[]),
        ), patch(
            "pawnai_matrix.callbacks.room",
            return_value=SimpleNamespace(get_free_speak=lambda _: False),
        ):
            callbacks = Callbacks()
            callbacks.room_listener.store_message_text = AsyncMock()
            callbacks.conversation_commands.process = AsyncMock()

            await callbacks.message(matrix_room, event)

        callbacks.room_listener.store_message_text.assert_awaited_once_with(
            matrix_room,
            event,
            text_override="hello there",
        )
        callbacks.conversation_commands.process.assert_not_called()


class AudioProcessorFreeSpeakTests(unittest.IsolatedAsyncioTestCase):
    async def test_unprefixed_audio_transcript_is_ignored_when_free_speak_disabled(self):
        matrix_room = SimpleNamespace()
        event = SimpleNamespace()

        with patch(
            "pawnai_matrix.processors.audio_processor.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.processors.audio_processor.room",
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
            "pawnai_matrix.processors.audio_processor.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.processors.audio_processor.room",
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
            "pawnai_matrix.processors.audio_processor.config",
            return_value={"matrix.command_prefix": "!bob"},
        ), patch(
            "pawnai_matrix.processors.audio_processor.room",
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
            "speak": False,
            "tts_voice": None,
            "tts_language": None,
            "tts_model": None,
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

    def test_default_configuration_contains_default_session(self):
        room_id = "!room:example.com"
        manager = Room({}, None)

        conf = manager._create_default_configuration(room_id)

        self.assertEqual(conf["sessions"]["default"], room_id)
        self.assertEqual(conf["current_session"], "default")

    def test_build_configuration_heals_missing_session_state(self):
        room_id = "!room:example.com"
        manager = Room({}, None)
        conf = manager._build_configuration(
            expert_id=None,
            expert_name="",
            json_config={"echo": True, "free_speak": False, "users": {}},
            room_id=room_id,
        )

        self.assertEqual(conf["sessions"], {"default": room_id})
        self.assertEqual(conf["current_session"], "default")

    def test_create_session_persists_and_survives_reload(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")

        class FakeSession:
            def __init__(self):
                self.rc = None
                self.committed = False

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def scalar(self, _statement):
                return self.rc

            def add(self, obj):
                self.rc = obj

            def commit(self):
                self.committed = True

        class FakeStore:
            def __init__(self, session):
                self.session = session

            def get_session(self):
                return self.session

        session = FakeSession()
        manager = Room({}, FakeStore(session))
        manager.get(matrix_room)
        manager.create_session(matrix_room, "alpha")

        self.assertTrue(session.committed)
        self.assertEqual(manager.get_current_session_alias(matrix_room), "alpha")
        self.assertEqual(
            manager.get_current_session_id(matrix_room),
            "!room:example.com::session::alpha",
        )


class RoomCommandHelpTests(unittest.IsolatedAsyncioTestCase):
    async def test_incomplete_free_speak_set_shows_room_help(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(sender="@admin:example.com")
        send_text = AsyncMock()

        with patch(
            "pawnai_matrix.commands.system_commands.send_text_to_room",
            new=send_text,
        ), patch(
            "pawnai_matrix.utils.chat.send_text_to_room",
            new=send_text,
        ), patch(
            "pawnai_matrix.client",
            return_value=SimpleNamespace(),
        ), patch(
            "pawnai_matrix.config",
            return_value={"matrix.power_users": ["@admin:example.com"]},
        ):
            commands = SystemCommands()
            commands._room_commands = RoomConfigCommands()

            handled = await commands.process(" room set free_speak", matrix_room, event)

        self.assertTrue(handled)
        send_text.assert_awaited_once()
        help_text = send_text.await_args.args[2]
        self.assertIn("room set free-speak (on|off)", help_text)


class SessionCommandsTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_current_reports_active_session(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(sender="@user:example.com")

        class FakeRoomManager:
            DEFAULT_SESSION_ALIAS = "default"

            @staticmethod
            def get_current_session_alias(_room):
                return "default"

            @staticmethod
            def get_current_session_id(_room):
                return "!room:example.com"

            @staticmethod
            def get_sessions(_room):
                return {"default": "!room:example.com"}

        send_text = AsyncMock()

        with patch(
            "pawnai_matrix.commands.session_commands.room",
            return_value=FakeRoomManager(),
        ), patch(
            "pawnai_matrix.commands.session_commands.client",
            return_value=SimpleNamespace(),
        ), patch(
            "pawnai_matrix.commands.session_commands.send_text_to_room",
            new=send_text,
        ):
            commands = SessionCommands()
            handled = await commands._session(["current"], matrix_room, event)

        self.assertTrue(handled)
        message = send_text.await_args.args[2]
        self.assertIn("Current session: `default`", message)

    async def test_session_ls_lists_all_sessions_and_marks_current(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(sender="@user:example.com")

        class FakeRoomManager:
            DEFAULT_SESSION_ALIAS = "default"

            @staticmethod
            def get_current_session_alias(_room):
                return "alpha"

            @staticmethod
            def get_current_session_id(_room):
                return "!room:example.com::session::alpha"

            @staticmethod
            def get_sessions(_room):
                return {
                    "default": "!room:example.com",
                    "alpha": "!room:example.com::session::alpha",
                }

        send_text = AsyncMock()

        with patch(
            "pawnai_matrix.commands.session_commands.room",
            return_value=FakeRoomManager(),
        ), patch(
            "pawnai_matrix.commands.session_commands.client",
            return_value=SimpleNamespace(),
        ), patch(
            "pawnai_matrix.commands.session_commands.send_text_to_room",
            new=send_text,
        ):
            commands = SessionCommands()
            handled = await commands._session(["ls"], matrix_room, event)

        self.assertTrue(handled)
        message = send_text.await_args.args[2]
        self.assertIn("`default` -> `!room:example.com`", message)
        self.assertIn("`alpha` -> `!room:example.com::session::alpha` (current)", message)

    async def test_session_new_creates_and_switches(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(sender="@user:example.com")

        class FakeClient:
            def reset_chat_engine(self):
                pass

        class FakeRoomManager:
            DEFAULT_SESSION_ALIAS = "default"

            def __init__(self):
                self.sessions = {"default": matrix_room.room_id}
                self.current_alias = "default"
                self.client = FakeClient()

            def get_current_session_alias(self, _room):
                return self.current_alias

            def get_current_session_id(self, _room):
                return self.sessions[self.current_alias]

            def get_sessions(self, _room):
                return self.sessions

            def create_session(self, _room, alias):
                if alias in self.sessions:
                    raise ValueError(f"Session `{alias}` already exists.")
                self.sessions[alias] = f"{matrix_room.room_id}::session::{alias}"
                self.current_alias = alias
                return self.sessions[alias]

            def use_session(self, _room, alias):
                if alias not in self.sessions:
                    raise ValueError(f"Session `{alias}` not found.")
                self.current_alias = alias
                return self.sessions[alias]

            def get_client(self, _room):
                return self.client

        send_text = AsyncMock()
        manager = FakeRoomManager()

        with patch(
            "pawnai_matrix.commands.session_commands.room",
            return_value=manager,
        ), patch(
            "pawnai_matrix.commands.session_commands.client",
            return_value=SimpleNamespace(),
        ), patch(
            "pawnai_matrix.commands.session_commands.send_text_to_room",
            new=send_text,
        ):
            commands = SessionCommands()
            handled = await commands._session(["new", "alpha"], matrix_room, event)

        self.assertTrue(handled)
        self.assertEqual(manager.current_alias, "alpha")
        self.assertIn("alpha", manager.sessions)
        self.assertEqual(
            manager.sessions["alpha"],
            "!room:example.com::session::alpha",
        )

    async def test_invalid_session_alias_does_not_create_session(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(sender="@user:example.com")

        class FakeRoomManager:
            DEFAULT_SESSION_ALIAS = "default"

            def __init__(self):
                self.sessions = {"default": matrix_room.room_id}
                self.current_alias = "default"

            def get_current_session_alias(self, _room):
                return self.current_alias

            def get_current_session_id(self, _room):
                return self.sessions[self.current_alias]

            def get_sessions(self, _room):
                return self.sessions

            def create_session(self, _room, alias):
                self.sessions[alias] = f"{matrix_room.room_id}::session::{alias}"
                self.current_alias = alias
                return self.sessions[alias]

        send_text = AsyncMock()
        manager = FakeRoomManager()

        with patch(
            "pawnai_matrix.commands.session_commands.room",
            return_value=manager,
        ), patch(
            "pawnai_matrix.commands.session_commands.client",
            return_value=SimpleNamespace(),
        ), patch(
            "pawnai_matrix.commands.session_commands.send_text_to_room",
            new=send_text,
        ):
            commands = SessionCommands()
            handled = await commands._session(["new", "Alpha Session"], matrix_room, event)

        self.assertTrue(handled)
        self.assertEqual(manager.current_alias, "default")
        self.assertEqual(manager.sessions, {"default": "!room:example.com"})

    async def test_session_reset_targets_current_session(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(sender="@user:example.com")

        class FakeClient:
            def __init__(self):
                self.reset_chat_engine = Mock()

        class FakeRoomManager:
            DEFAULT_SESSION_ALIAS = "default"

            def __init__(self):
                self.sessions = {
                    "default": matrix_room.room_id,
                    "alpha": f"{matrix_room.room_id}::session::alpha",
                }
                self.current_alias = "alpha"
                self.client = FakeClient()

            def get_current_session_alias(self, _room):
                return self.current_alias

            def get_current_session_id(self, _room):
                return self.sessions[self.current_alias]

            def get_sessions(self, _room):
                return self.sessions

            def get_client(self, _room):
                return self.client

        send_text = AsyncMock()
        manager = FakeRoomManager()

        with patch(
            "pawnai_matrix.commands.session_commands.room",
            return_value=manager,
        ), patch(
            "pawnai_matrix.commands.session_commands.client",
            return_value=SimpleNamespace(),
        ), patch(
            "pawnai_matrix.commands.session_commands.send_text_to_room",
            new=send_text,
        ):
            commands = SessionCommands()
            handled = await commands._session(["reset"], matrix_room, event)

        self.assertTrue(handled)
        manager.client.reset_chat_engine.assert_called_once()

    async def test_session_use_missing_alias_keeps_current_session(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(sender="@user:example.com")

        class FakeRoomManager:
            DEFAULT_SESSION_ALIAS = "default"

            def __init__(self):
                self.sessions = {"default": matrix_room.room_id}
                self.current_alias = "default"

            def get_current_session_alias(self, _room):
                return self.current_alias

            def get_current_session_id(self, _room):
                return self.sessions[self.current_alias]

            def get_sessions(self, _room):
                return self.sessions

            def use_session(self, _room, alias):
                if alias not in self.sessions:
                    raise ValueError(f"Session `{alias}` not found.")
                self.current_alias = alias
                return self.sessions[alias]

        send_text = AsyncMock()
        manager = FakeRoomManager()

        with patch(
            "pawnai_matrix.commands.session_commands.room",
            return_value=manager,
        ), patch(
            "pawnai_matrix.commands.session_commands.client",
            return_value=SimpleNamespace(),
        ), patch(
            "pawnai_matrix.commands.session_commands.send_text_to_room",
            new=send_text,
        ):
            commands = SessionCommands()
            handled = await commands._session(["use", "alpha"], matrix_room, event)

        self.assertTrue(handled)
        self.assertEqual(manager.current_alias, "default")


if __name__ == "__main__":
    unittest.main()
