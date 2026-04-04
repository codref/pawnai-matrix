import datetime
import shlex
import importlib.metadata
from nio import MatrixRoom, RoomMessageText

from pawnai_bob.utils import send_text_to_room
from pawnai_bob.utils.decorators import matrix_command, power_user_function
from pawnai_bob import client, room, config, get_started_on, get_debug_message, has_debug_message
from pawnai_bob.commands.expert_commands import ExpertCommands
from pawnai_bob.commands.room_config_commands import RoomConfigCommands
from pawnai_bob.commands.index_commands import IndexCommands


class SystemCommands:

    def __init__(self):
        self._expert_commands = ExpertCommands()
        self._room_commands = RoomConfigCommands()
        self._index_commands = IndexCommands()

    async def process(self, command: str, matrix_room: MatrixRoom,
                      event: RoomMessageText):
        """
        Process the command
        Args:
            command: The command and arguments.
            matrix_room: The room the command was sent in.
            event: The event describing the command.
        """

        try:
            args = shlex.split(command,
                               posix=False)[1:]  # shlex allows better splitting
        except Exception as e:
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f"Error parsing the command: {e}",
                                    notice=True,
                                    event=event)
            return True

        if command.startswith("help"):
            return await self._help(args, matrix_room, event)
        if command.startswith("info"):
            return await self._info(args, matrix_room, event)
        if command.startswith("prompt"):
            return await self._prompt(args, matrix_room, event)
        if command.startswith("context"):
            return await self._context(args, matrix_room, event)
        if command.startswith("model"):
            return await self._index_commands._model(args, matrix_room, event)
        if command.startswith("debug"):
            return await self._debug(args, matrix_room, event)
        if command.startswith("expert"):
            return await self._expert_commands._expert(args, matrix_room, event)
        if command.startswith("room"):
            return await self._room_commands._room(args, matrix_room, event)
        return False

    @matrix_command
    async def _debug(self, opts, matrix_room, event):
        """
        Print useful debug information.

        Usage:
          debug message
        """

        if 'message' in opts and opts['message']:
            if not has_debug_message():
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"No message debug info found.",
                                        notice=True,
                                        event=event)
            else:
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    get_debug_message(),
                    notice=True,
                    event=event)

        return True

    async def _help(self, args, matrix_room, event):
        """Print available commands"""
        version = importlib.metadata.version('pawnai_bob')
        uptime = datetime.datetime.now() - get_started_on()
        await send_text_to_room(client(),
                                matrix_room.room_id,
                                f"""
            Matrix Bob version {version}.
            Available commands are:
            !bob help       this message
            !bob info       shows version, uptime and other info
            !bob prompt     manage LLM prompt
            !bob context    change context size
            !bob model      change LLM
            !bob expert     manage experts
            !bob room       manage room configurations
            !bob debug      show debug information
            """, notice=True,
                                event=event)
        return True

    async def _info(self, args, matrix_room, event):
        """Print some information"""
        version = importlib.metadata.version('pawnai_bob')
        uptime = datetime.datetime.now() - get_started_on()
        await send_text_to_room(client(),
                                matrix_room.room_id,
                                f"""Matrix Bob version {version}.
            Uptime is {uptime}
            """, notice=True,
                                event=event)
        return True

    @matrix_command
    async def _prompt(self, opts, matrix_room, event):
        """
        Set the LLM chat prompt value.

        Usage:
          prompt
          prompt set <prompt_text>
          prompt reset
        """

        if 'set' in opts and opts['set']:
            room().get_client(matrix_room).set_prompt(opts['<prompt_text>'])
            room().get_client(matrix_room).init_chat_engine()
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"LLM prompt is now `{opts['<prompt_text>']}`.",
                notice=True,
                event=event)

        # Reset the prompt to the default one configured
        elif 'reset' in opts and opts['reset']:
            room().get_client(matrix_room).set_prompt(
                config().get('openai.default_prompt'))
            room().get_client(matrix_room).init_chat_engine()
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"LLM prompt has been reset to the default `{config().get('openai.default_prompt')}`.",
                notice=True,
                event=event)

        # Print current chat prompt
        else:
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"LLM prompt is `{room().get_client(matrix_room).prompt}`.",
                notice=True,
                event=event)

        return True

    @matrix_command
    async def _context(self, opts, matrix_room, event):
        """
        Manages the LLM chat context.
        Length value consists on the amount of tokens kept in the context while chatting.

        Usage:
          context length [<tokens>]
          context reset
        """

        # Set and get the context length
        if 'length' in opts and opts['length']:
            if '<tokens>' in opts and opts['<tokens>']:
                room().get_client(matrix_room).set_context_length(
                    int(opts['<tokens>']))
                room().get_client(matrix_room).init_chat_engine()
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    f"Context has been reset and the length is now set to `{opts['<tokens>']}` tokens",
                    notice=True,
                    event=event)
            else:
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    f"Context length is `{room().get_client(matrix_room).context_length}` tokens",
                    notice=True,
                    event=event)

        # Reset the chat context memory
        elif 'reset' in opts and opts['reset']:
            room().get_client(matrix_room).reset_chat_engine()
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f"Context has been reset!",
                                    notice=True,
                                    event=event)
        return True

