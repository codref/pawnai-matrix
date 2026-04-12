import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from pawnai_matrix.commands.conversation_commands import (
    ConversationCommands,
    LISTEN_ONLY_BYPASS_TOKEN,
    THINKING_REACTION,
)


def _build_room_state(response_text: str, speak: bool):
    chat_engine = SimpleNamespace(chat=Mock(return_value=response_text))
    return SimpleNamespace(
        get_users=lambda _: {},
        get_speak=lambda _: speak,
        get_client=lambda _: SimpleNamespace(chat_engine=chat_engine),
        get_echo=lambda _: False,
    )


class ConversationCommandsTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_suppresses_client_output_when_bypass_token_is_present(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(
            event_id="$event",
            source={"sender": "@user:example.com", "content": {}},
        )
        mock_client = SimpleNamespace(room_typing=AsyncMock())
        mock_room = _build_room_state(LISTEN_ONLY_BYPASS_TOKEN, speak=False)

        with patch(
            "pawnai_matrix.commands.conversation_commands.client",
            return_value=mock_client,
        ), patch(
            "pawnai_matrix.commands.conversation_commands.room",
            return_value=mock_room,
        ), patch(
            "pawnai_matrix.commands.conversation_commands.react_to_event",
            new=AsyncMock(),
        ) as react_to_event_mock, patch(
            "pawnai_matrix.commands.conversation_commands.send_text_to_room",
            new=AsyncMock(),
        ) as send_text_to_room_mock, patch(
            "pawnai_matrix.commands.conversation_commands.set_debug_message",
        ) as set_debug_message_mock:
            commands = ConversationCommands()
            commands._tts_processor.process = AsyncMock()

            response = await commands._chat("hello", matrix_room, event, replies=[])

        self.assertEqual(response, LISTEN_ONLY_BYPASS_TOKEN)
        react_to_event_mock.assert_awaited_once_with(
            mock_client, matrix_room.room_id, event.event_id, THINKING_REACTION
        )
        send_text_to_room_mock.assert_not_called()
        commands._tts_processor.process.assert_not_called()
        set_debug_message_mock.assert_called_once()
        mock_client.room_typing.assert_any_await(
            matrix_room.room_id, True, timeout=120000
        )
        mock_client.room_typing.assert_any_await(matrix_room.room_id, False)

    async def test_chat_suppresses_tts_when_bypass_token_is_present(self):
        matrix_room = SimpleNamespace(room_id="!room:example.com")
        event = SimpleNamespace(
            event_id="$event",
            source={"sender": "@user:example.com", "content": {}},
        )
        mock_client = SimpleNamespace(room_typing=AsyncMock())
        mock_room = _build_room_state(LISTEN_ONLY_BYPASS_TOKEN, speak=True)

        with patch(
            "pawnai_matrix.commands.conversation_commands.client",
            return_value=mock_client,
        ), patch(
            "pawnai_matrix.commands.conversation_commands.room",
            return_value=mock_room,
        ), patch(
            "pawnai_matrix.commands.conversation_commands.react_to_event",
            new=AsyncMock(),
        ), patch(
            "pawnai_matrix.commands.conversation_commands.send_text_to_room",
            new=AsyncMock(),
        ) as send_text_to_room_mock:
            commands = ConversationCommands()
            commands._tts_processor.process = AsyncMock()

            await commands._chat("hello", matrix_room, event, replies=[])

        send_text_to_room_mock.assert_not_called()
        commands._tts_processor.process.assert_not_called()

