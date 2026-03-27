import functools
import shlex
import tempfile
import base64
from nio import MatrixRoom, RoomMessageText
from docopt import docopt, DocoptExit
from pawnai_bob import client, room, settings, set_debug_message
from pawnai_bob.utils import send_text_to_room, send_image_to_room, react_to_event

def matrix_command(func):

    @functools.wraps(func)
    async def fn(self, args, matrix_room, event):
        try:
            opts = docopt(fn.__doc__, args)

        except DocoptExit as e:
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    fn.__doc__,
                                    event=event)
            return True

        return await func(self, opts, matrix_room, event)

    return fn

class VisionCommands:

    async def process(self, command: str, matrix_room: MatrixRoom,
                      event: RoomMessageText):
        """
        Process the command
        Args:
            command: The command and arguments.
            matrix_room: The room the command was sent in.
            event: The event describing the command.
        """

        command = command
        try:
            args = shlex.split(command,
                           posix=False)[1:]  # shlex allows better splitting
        except Exception as e:
            await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"Error parsing the command: {e}",
                                        event=event)
            return True

        if command.startswith("draw"):
            return await self._draw(args, matrix_room, event)
        return False

    @matrix_command
    async def _draw(self, opts, matrix_room, event):
        """
        Text to image

        Usage:
          draw <input> [<model>]
        """

        # React with a thinking emoji
        reaction = "🤔"
        await react_to_event(client(), matrix_room.room_id, event.event_id,
                             reaction)
        
        # Send a start typing event, with a fixed timeout
        # TODO estimate the typing duration or stream back the reply!
        await client().room_typing(matrix_room.room_id, True, timeout=120000)
       
        try:
            model = ""
            if "<model>" in opts:
                model = opts['<model>']
            response = room().get(matrix_room)['vision_client'].create_image(opts['<input>'], model=model)
            if response.status_code != 200:
                await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        f"Cannot generate the image [{response.status_code}]",
                        event=event)
                return True
                
            with tempfile.TemporaryDirectory(
                dir=settings().temp_path, ignore_cleanup_errors=True) as temp_path:
                with open(f"{temp_path}/image.png", 'wb') as f:
                    f.write(base64.b64decode(response.json()["image"]))

                await send_image_to_room(
                    client(),
                    matrix_room.room_id,
                    f"{temp_path}/image.png"
                )
        
        except Exception as e:
            if room().get(matrix_room)['echo']:
                await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f'Error: {e}',
                                    event=event)
            set_debug_message(f"Cannot generate the image:\n{e}")

        finally:
            await client().room_typing(matrix_room.room_id, False)

        return True
   