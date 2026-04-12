import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pawnai_matrix.utils.chat import LISTEN_ONLY_BYPASS_TOKEN, send_text_to_room


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

