import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pawnai_matrix.openai_client import OpenAIClient
from pawnai_matrix.room import Room


class OpenAIClientSessionTests(unittest.TestCase):
    @patch("pawnai_matrix.openai_client.OpenAI")
    def test_chat_passes_session_id_as_user(self, openai_cls):
        create = Mock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
            )
        )
        openai_cls.return_value = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            )
        )

        client = OpenAIClient({}, "!room:example.com")
        client.set_session_id("session-123")

        response = client.chat("hello")

        self.assertEqual(response, "ok")
        create.assert_called_once_with(
            model="pawn-agent",
            messages=[{"role": "user", "content": "hello"}],
            user="session-123",
        )

    @patch("pawnai_matrix.openai_client.OpenAI")
    def test_reset_passes_session_id_as_user(self, openai_cls):
        create = Mock()
        openai_cls.return_value = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            )
        )

        client = OpenAIClient({}, "!room:example.com")
        client.set_session_id("session-123")
        client.reset_chat_engine()

        create.assert_called_once_with(
            model="pawn-agent",
            messages=[{"role": "user", "content": "/reset"}],
            user="session-123",
        )


class RoomSessionBindingTests(unittest.TestCase):
    @patch("pawnai_matrix.room.OpenAIClient")
    def test_get_client_sets_active_session_id_on_client(self, openai_client_cls):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        client_instance = Mock()
        openai_client_cls.return_value = client_instance

        manager = Room({}, None)
        conf = manager._create_default_configuration(matrix_room.room_id)
        conf["sessions"]["alpha"] = manager.build_session_id(matrix_room, "alpha")
        conf["current_session"] = "alpha"
        manager.configuration[matrix_room.room_id] = conf

        client = manager.get_client(matrix_room)

        self.assertIs(client, client_instance)
        client_instance.set_session_id.assert_called_once_with(
            "!room:example.com::session::alpha"
        )

    def test_resolve_session_id_uses_current_room_session_for_non_threaded_event(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        manager = Room({}, None)
        conf = manager._create_default_configuration(matrix_room.room_id)
        conf["sessions"]["alpha"] = manager.build_session_id(matrix_room, "alpha")
        conf["current_session"] = "alpha"
        manager.configuration[matrix_room.room_id] = conf

        event = SimpleNamespace(source={"content": {}})

        self.assertEqual(
            manager.resolve_session_id(matrix_room, event),
            "!room:example.com::session::alpha",
        )

    def test_resolve_session_id_uses_thread_root_for_threaded_event(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        manager = Room({}, None)
        manager.configuration[matrix_room.room_id] = manager._create_default_configuration(
            matrix_room.room_id
        )
        event = SimpleNamespace(
            source={
                "content": {
                    "m.relates_to": {
                        "rel_type": "m.thread",
                        "event_id": "$root",
                        "m.in_reply_to": {"event_id": "$latest"},
                    }
                }
            }
        )

        self.assertEqual(
            manager.resolve_session_id(matrix_room, event),
            "!room:example.com::thread::$root",
        )

    def test_resolve_session_id_reuses_same_thread_session_for_same_root(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        manager = Room({}, None)
        manager.configuration[matrix_room.room_id] = manager._create_default_configuration(
            matrix_room.room_id
        )
        first_event = SimpleNamespace(
            source={
                "content": {
                    "m.relates_to": {
                        "rel_type": "m.thread",
                        "event_id": "$root",
                        "m.in_reply_to": {"event_id": "$a"},
                    }
                }
            }
        )
        second_event = SimpleNamespace(
            source={
                "content": {
                    "m.relates_to": {
                        "rel_type": "m.thread",
                        "event_id": "$root",
                        "m.in_reply_to": {"event_id": "$b"},
                    }
                }
            }
        )

        self.assertEqual(
            manager.resolve_session_id(matrix_room, first_event),
            manager.resolve_session_id(matrix_room, second_event),
        )

    def test_resolve_session_id_uses_distinct_sessions_for_distinct_roots(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        manager = Room({}, None)
        manager.configuration[matrix_room.room_id] = manager._create_default_configuration(
            matrix_room.room_id
        )
        first_event = SimpleNamespace(
            source={
                "content": {
                    "m.relates_to": {
                        "rel_type": "m.thread",
                        "event_id": "$root-a",
                    }
                }
            }
        )
        second_event = SimpleNamespace(
            source={
                "content": {
                    "m.relates_to": {
                        "rel_type": "m.thread",
                        "event_id": "$root-b",
                    }
                }
            }
        )

        self.assertNotEqual(
            manager.resolve_session_id(matrix_room, first_event),
            manager.resolve_session_id(matrix_room, second_event),
        )

    @patch("pawnai_matrix.room.OpenAIClient")
    def test_get_client_sets_thread_session_id_for_threaded_event(self, openai_client_cls):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        client_instance = Mock()
        openai_client_cls.return_value = client_instance

        manager = Room({}, None)
        manager.configuration[matrix_room.room_id] = manager._create_default_configuration(
            matrix_room.room_id
        )
        event = SimpleNamespace(
            source={
                "content": {
                    "m.relates_to": {
                        "rel_type": "m.thread",
                        "event_id": "$root",
                        "m.in_reply_to": {"event_id": "$latest"},
                    }
                }
            }
        )

        client = manager.get_client(matrix_room, event)

        self.assertIs(client, client_instance)
        client_instance.set_session_id.assert_called_once_with(
            "!room:example.com::thread::$root"
        )
