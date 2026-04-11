from nio import MatrixRoom, RoomMessageText

from pawnai_matrix.utils import send_text_to_room, react_to_event, get_reply_body
from pawnai_matrix import client, room, set_debug_message
from pawnai_matrix.processors.tts_processor import TTSProcessor


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

    async def _chat(self, message: str, matrix_room: MatrixRoom, event,
                    replies: list):

        # React with a thinking emoji
        reaction = "🤔"
        await react_to_event(client(), matrix_room.room_id, event.event_id,
                             reaction)

        # Send a start typing event, with a fixed timeout
        # TODO estimate the typing duration or stream back the reply!
        await client().room_typing(matrix_room.room_id, True, timeout=120000)

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

            response = room().get_client(matrix_room).chat_engine.chat(message)
            response_text = str(response)

            if room().get_speak(matrix_room):
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
            await client().room_typing(matrix_room.room_id, False)

        return True
