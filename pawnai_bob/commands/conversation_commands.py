from nio import MatrixRoom, RoomMessageText

from pawnai_bob.utils import (send_text_to_room, react_to_event,
                                       download_event_resources,
                                       get_image_url_from_path, get_reply_body)
from pawnai_bob import client, room, g, set_debug_vision, set_debug_message


class ConversationCommands:

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

        # We do not have other conversation functions, but the default return should be false
        # return False

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
            # Check if among the replies we have an image
            replies_body = ""
            for reply in replies:
                if reply.source["content"]["msgtype"] == "m.image":
                    async with download_event_resources(reply) as temp_path:
                        image_url = get_image_url_from_path(temp_path)
                        
                        # return immediately with no error if the image is not supported
                        if image_url is None:
                            return ""

                        response = room().get(
                            matrix_room)['vision_client'].query_image(
                                image_url, message)
                        
                        # store debug information
                        set_debug_vision(response)

                        # if single step, we just return the multimodal model response
                        if not room().get(matrix_room)['vision-two-steps']:
                            await send_text_to_room(client(),
                                                    matrix_room.room_id,
                                                    response,
                                                    event=event)
                            # Return the answer, as it might be added to the index as well!
                            return response
                        replies_body += response + "\n"
                        
                else:
                    replies_body += get_reply_body(reply) + "\n"

            # attempt the user mapping
            sender = event.source.get('sender')
            if sender in room().get(matrix_room)['users']:
                message = f"{room().get(matrix_room)['users'][sender]}: " + message

            # If the message is a reply, use the replied messages as injected context
            if replies_body != "":
                # message = "Consider just the following conversation: " + concat_replies_body(replies) + ".\n" + message
                message = f"{replies_body}\n{message}"

            response = room().get(matrix_room)['client'].chat_engine.chat(
                message)
            # Send back the answer
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    str(response),
                                    event=event)
            # Return the answer, as it might be added to the index as well!
            return str(response)
        except Exception as e:
            if room().get(matrix_room)['echo']:
                await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f'Error: {e}',
                                    event=event)
            set_debug_message(f"Cannot generate a response:\n{e}")

        finally:
            await client().room_typing(matrix_room.room_id, False)

        return True
