from nio import MatrixRoom, RoomMessageText

from pawnai_matrix.utils import (
    get_reply_body,
    get_thread_root_event_id,
    react_to_event,
    send_text_to_room,
)
from pawnai_matrix import client, room, set_debug_message
from pawnai_matrix.processors.tts_processor import TTSProcessor

LISTEN_ONLY_BYPASS_TOKEN = "PAWN_LISTEN_ONLY_BYPASS"
THINKING_REACTION = "⋯"
THREAD_THINKING_MESSAGE = "Thinking..."


class ConversationCommands:

    def __init__(self):
        self._tts_processor = TTSProcessor()

    async def process(self, command: str, matrix_room: MatrixRoom,
                      event: RoomMessageText, replies):
        """
        Process the command
        Args:
            command: The command and arguments.
            matrix_room: The room the command was sent in.
            event: The event describing the command.
        """

        # This should be the last command to execute as it's a generic conversation entrypoint
        return await self._chat(command, matrix_room, event, replies)

    async def _start_thinking_indicator(self, matrix_room: MatrixRoom, event):
        if get_thread_root_event_id(event):
            return await send_text_to_room(
                client(),
                matrix_room.room_id,
                THREAD_THINKING_MESSAGE,
                notice=True,
                event=event,
            )

        await client().room_typing(matrix_room.room_id, True, timeout=120000)
        return None

    async def _stop_thinking_indicator(self, matrix_room: MatrixRoom, indicator_response):
        if indicator_response is not None:
            indicator_event_id = getattr(indicator_response, "event_id", None)
            if indicator_event_id:
                await client().room_redact(
                    matrix_room.room_id,
                    indicator_event_id,
                    reason="Response ready",
                )
            return

        await client().room_typing(matrix_room.room_id, False)

    async def _chat(self, message: str, matrix_room: MatrixRoom, event,
                    replies: list):

        await react_to_event(
            client(),
            matrix_room.room_id,
            event.event_id,
            THINKING_REACTION,
        )

        # Typing notifications are room-scoped in Matrix, so threads get a local
        # placeholder message instead of lighting up the main timeline.
        thinking_indicator = await self._start_thinking_indicator(matrix_room, event)

        try:
            replies_body = ""
            for reply in replies:
                replies_body += get_reply_body(reply) + "\n"

            # attempt the user mapping
            sender = event.source.get('sender')
            if sender in room().get_users(matrix_room):
                message = f"{room().get_users(matrix_room)[sender]}: " + message

            # If the message is a reply, use the replied messages as injected context
            if replies_body != "":
                message = f"{replies_body}\n{message}"

            if room().get_speak(matrix_room):
                message = (
                    "[Your response will be read aloud via text-to-speech. "
                    "Use plain prose only — no markdown, no bullet points, no headers, "
                    "no code blocks, no special characters. Write as natural spoken narration. "
                    "Use punctuation to convey structure and emphasis: colons to introduce lists, "
                    "commas and semicolons to separate items, dashes for asides, "
                    "and full stops to mark clear pauses.]\n\n"
                    + message
                )

            response = room().get_client(matrix_room, event).chat_engine.chat(message)
            response_text = str(response)

            bypass_client_output = LISTEN_ONLY_BYPASS_TOKEN in response_text

            if bypass_client_output:
                set_debug_message(
                    "Skipping client output due to PAWN_LISTEN_ONLY_BYPASS token."
                )
            elif room().get_speak(matrix_room):
                await self._tts_processor.process(matrix_room, event, response_text)
            else:
                # Send back the answer
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        response_text,
                                        event=event)
            # Return the answer, as it might be added to the index as well!
            return response_text
        except Exception as e:
            if room().get_echo(matrix_room):
                await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f'Error: {e}',
                                    event=event)
            set_debug_message(f"Cannot generate a response:\n{e}")

        finally:
            await self._stop_thinking_indicator(matrix_room, thinking_indicator)

        return True
