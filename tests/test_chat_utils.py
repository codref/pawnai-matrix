import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pawnai_matrix.utils.chat import (
    LISTEN_ONLY_BYPASS_TOKEN,
    get_thread_root_event_id,
    send_text_to_room,
)


class ChatUtilsTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_text_to_room_skips_bypass_token(self):
        client = SimpleNamespace(room_send=AsyncMock())

        result = await send_text_to_room(
            client=client,
            room_id="!room:example.com",
            message=LISTEN_ONLY_BYPASS_TOKEN,
        )

        self.assertIsNone(result)
        client.room_send.assert_not_awaited()

    async def test_send_text_to_room_sends_regular_message(self):
        expected_response = object()
        client = SimpleNamespace(room_send=AsyncMock(return_value=expected_response))

        result = await send_text_to_room(
            client=client,
            room_id="!room:example.com",
            message="Hello world",
        )

        self.assertIs(result, expected_response)
        client.room_send.assert_awaited_once()

    def test_get_thread_root_event_id_returns_root_for_thread_event(self):
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

        self.assertEqual(get_thread_root_event_id(event), "$root")

    def test_get_thread_root_event_id_returns_none_for_malformed_relation(self):
        malformed_events = [
            SimpleNamespace(source={"content": {}}),
            SimpleNamespace(source={"content": {"m.relates_to": {}}}),
            SimpleNamespace(
                source={"content": {"m.relates_to": {"rel_type": "m.thread"}}}
            ),
            SimpleNamespace(
                source={
                    "content": {
                        "m.relates_to": {"rel_type": "m.thread", "event_id": ""}
                    }
                }
            ),
            SimpleNamespace(
                source={
                    "content": {
                        "m.relates_to": {"rel_type": "m.in_reply_to", "event_id": "$x"}
                    }
                }
            ),
        ]

        for event in malformed_events:
            with self.subTest(event=event):
                self.assertIsNone(get_thread_root_event_id(event))
