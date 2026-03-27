import datetime
import functools
import json
import shlex
from nio import MatrixRoom, RoomMessageText
import importlib.metadata
from sqlalchemy import select

from pawnai_bob.utils import send_text_to_room
from pawnai_bob import client, room, g, settings, store, get_started_on, get_debug_message, has_debug_message, get_debug_vision, has_debug_vision, get_debug_whispered, has_debug_whispered
from pawnai_bob.models import Expert, RoomConfiguration

from docopt import docopt, DocoptExit

from pawnai_bob import settings


def matrix_command(func):
    @functools.wraps(func)
    async def fn(self, args, matrix_room, event):
        try:
            opts = docopt(fn.__doc__, args)

        except DocoptExit as e:
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    fn.__doc__,
                                    notice=True,
                                    event=event)
            return True

        return await func(self, opts, matrix_room, event)

    return fn


def power_user_function(func):
    @functools.wraps(func)
    async def fn(self, args, matrix_room, event):
        if event.sender not in settings().power_users:
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                "This function requires power user rights!",
                notice=True,
                event=event)
            return True

        return await func(self, args, matrix_room, event)

    return fn


class SystemCommands:

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
        if command.startswith("index"):
            return await self._index(args, matrix_room, event)
        if command.startswith("model"):
            return await self._model(args, matrix_room, event)
        if command.startswith("embed"):
            return await self._embed(args, matrix_room, event)
        if command.startswith("debug"):
            return await self._debug(args, matrix_room, event)
        if command.startswith("whisper"):
            return await self._whisper(args, matrix_room, event)
        if command.startswith("expert"):
            return await self._expert(args, matrix_room, event)
        if command.startswith("room"):
            return await self._room(args, matrix_room, event)
        return False

    @matrix_command
    async def _debug(self, opts, matrix_room, event):
        """
        Print useful debug information.

        Usage:
          debug whisper
          debug vision
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

        if 'whisper' in opts and opts['whisper']:
            if not has_debug_whispered():
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"No whispered text found.",
                                        notice=True,
                                        event=event)
            else:
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    f"Last whispered text was `{get_debug_whispered()}`.",
                    notice=True,
                    event=event)
        elif 'vision' in opts and opts['vision']:
            if not has_debug_vision():
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"No vision text found.",
                                        notice=True,
                                        event=event)
            else:
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    f"Last seen image contains `{get_debug_vision()}`.",
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
            !bob index      manage index database (qdrant)
            !bob model      change LLM
            !bob embed      change embed model
            !bob whisper    configure whisper (speech-to-text)
            !bob expert     manage experts
            !bob room       manage room configurations
            !bob debug      show debug information
            !bob draw       draw a picture given a prompt (text-to-image)
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
            # new_prompt = " ".join(opts['<prompt_text>'])
            room().get(matrix_room)['client'].set_prompt(opts['<prompt_text>'])
            room().get(matrix_room)['client'].init_chat_engine()
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"LLM prompt is now `{opts['<prompt_text>']}`.",
                notice=True,
                event=event)

        # Reset the prompt to the default one configured
        elif 'reset' in opts and opts['reset']:
            room().get(matrix_room)['client'].set_prompt(
                settings().ollama_default_prompt)
            room().get(matrix_room)['client'].init_chat_engine()
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"LLM prompt has been reset to the default `{settings().openai_default_prompt}`.",
                notice=True,
                event=event)

        # Print current chat prompt
        else:
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"LLM prompt is `{room().get(matrix_room)['client'].prompt}`.",
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
                room().get(matrix_room)['client'].set_context_length(
                    int(opts['<tokens>']))
                room().get(matrix_room)['client'].init_chat_engine()
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
                    f"Context length is `{room().get(matrix_room)['client'].context_length}` tokens",
                    notice=True,
                    event=event)

        # Reset the chat context memory
        elif 'reset' in opts and opts['reset']:
            room().get(matrix_room)['client'].reset_chat_engine()
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f"Context has been reset!",
                                    notice=True,
                                    event=event)
        return True

    @power_user_function
    @matrix_command
    async def _index(self, opts, matrix_room, event):
        """
        Manages the indexes collection
        Usage:
          index ls
          index set <new_collection_name>
          index fork <new_collection_name>
          index rm
          index chat (react|context)
          index info
        """

        old_collection_name = room().get(matrix_room)['client'].collection_name

        # List all available collections on Qdrant
        if 'ls' in opts and opts['ls']:
            result = room().get(matrix_room)['client'].client.get_collections()
            collections = ""
            for c in result.collections:
                if c.name == room().get(matrix_room)['client'].collection_name:
                    collections += f"**{c.name}**  \n"
                else:
                    collections += f"{c.name}  \n"
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f"""Available indexes:  
                {collections}
                """, notice=True,
                                    event=event)

        # Change collection, creates a new one if it does not exist
        elif 'set' in opts and opts['set']:
            room().get(matrix_room)['client'].set_collection_name(
                opts['<new_collection_name>'])
            room().get(matrix_room)['client'].init_index()
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"Active index is now `{opts['<new_collection_name>']}`. ",
                notice=True,
                event=event)

        # Forks the current collection into a new one
        elif 'fork' in opts and opts['fork']:
            # forked collections must have the same options of the source collection
            config = room().get(matrix_room)['client'].client.get_collection(
                collection_name=room()['client'].get(
                    room).collection_name).config
            result = room().get(
                matrix_room)['client'].client.create_collection(
                collection_name=opts['<new_collection_name>'],
                vectors_config=models.VectorParams(
                    size=config.params.vectors.size,
                    distance=config.params.vectors.distance),
                init_from=models.InitFrom(collection=room()['client'].get(
                    matrix_room).collection_name))

            # set fork as current collection
            room().get(matrix_room)['client'].set_collection_name(
                opts['<new_collection_name>'])
            room().get(matrix_room)['client'].init_index()

            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"Active index is now **{opts['<new_collection_name>']}** (forked from `{old_collection_name}`)",
                notice=True,
                event=event)

        # Deletes the current collection and set default the active one
        elif 'rm' in opts and opts['rm']:
            result = room().get(
                matrix_room)['client'].client.delete_collection(
                collection_name=room().get(
                    matrix_room)['client'].collection_name)

            if room().get(matrix_room)['client'].collection_name != "default":
                room().get(matrix_room)['client'].set_collection_name(
                    "default")
                room().get(matrix_room)['client'].init_index()
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    f"""Index `{old_collection_name}` has been deleted.  
                    Active index is now **default**.
                    """,
                    notice=True,
                    event=event)
            else:
                # default collection is created the moment we index something
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    f"""Index `{room().get(matrix_room)['client'].collection_name}` has been deleted.  
                    Active index is now `default`. It will be created as soon as new data is indexed.
                    """,
                    notice=True,
                    event=event)

        # Returns information about the current collection
        elif 'info' in opts and opts['info']:
            result = str(
                room().get(matrix_room)['client'].client.get_collection(
                    collection_name=room()['client'].get(
                        room).collection_name)).replace(",", ",\n").replace(
                "<", "(").replace(">", ")")
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"""Active index is `{room().get(matrix_room)['client'].collection_name}`.  

                {result}
                """, notice=True,
                event=event)
        elif 'chat' in opts and opts['chat']:
            if opts['react']:
                room().get(matrix_room)['client'].set_chat_mode("react")
            else:
                room().get(matrix_room)['client'].set_chat_mode("context")
            room().get(matrix_room)['client'].init_chat_engine()
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"Index is now using `{room().get(matrix_room)['client'].chat_mode}` chat mode.",
                notice=True,
                event=event)

        return True

    @power_user_function
    @matrix_command
    async def _model(self, opts, matrix_room, event):
        """
        Usage:
          model ls
          model set <model_name>
        """

        if 'ls' in opts and opts['ls']:
            available_models = "Available models:  \n"
            for model in settings().openai_llm_models:
                if model == room().get(matrix_room)['client'].llm_model:
                    available_models += f"**{model}**  \n"
                else:
                    available_models += f"{model}  \n"
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    available_models,
                                    notice=True,
                                    event=event)

        elif 'set' in opts and opts['set']:
            if opts['<model_name>'] not in settings().openai_llm_models:
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"LLM not allowed!",
                                        notice=True,
                                        event=event)
            else:
                room().get(matrix_room)['client'].set_llm_model(
                    opts['<model_name>'])
                room().get(matrix_room)['client'].init_llm()
                room().get(matrix_room)['client'].init_index()
                room().get(matrix_room)['client'].init_chat_engine()
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    f"LLM is now {room().get(matrix_room)['client'].llm_model}",
                    notice=True,
                    event=event)
        return True

    @power_user_function
    @matrix_command
    async def _vision(self, opts, matrix_room, event):
        """
        Usage:
          vision set two-steps (on|off)
        """
        if "two-steps" in opts and opts['two-steps']:
            flag = True if opts['on'] else False
            room().set_vision_two_steps(matrix_room, flag)
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f"Flag vision `two-steps` is now {flag}",
                                    notice=True,
                                    event=event)

        return True

    @power_user_function
    @matrix_command
    async def _embed(self, opts, matrix_room, event):
        """
        Usage:
          embed ls
          embed set <model_name>
        """

        if 'ls' in opts and opts['ls']:
            available_models = "Available embedding models:  \n"
            for model in settings().openai_embed_models:
                if model == room().get(matrix_room)['client'].embed_model:
                    available_models += f"**{model}**  \n"
                else:
                    available_models += f"{model}  \n"
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    available_models,
                                    notice=True,
                                    event=event)

        elif 'set' in opts and opts['set']:
            if opts['<model_name>'] not in settings().openai_embed_models:
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"Embedding model not allowed!",
                                        notice=True,
                                        event=event)
            else:
                room().get(matrix_room)['client'].set_embed_model(
                    opts['<model_name>'])
                room().get(matrix_room)['client'].init_llm()
                room().get(matrix_room)['client'].init_index()
                room().get(matrix_room)['client'].init_chat_engine()
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    f"Embedding model is now {room().get(matrix_room)['client'].embed_model}",
                    notice=True,
                    event=event)
        return True

    @power_user_function
    @matrix_command
    async def _whisper(self, opts, matrix_room, event):
        """
        Usage:
          whisper ls
          whisper set <model_name>
        """

        if 'ls' in opts and opts['ls']:
            available_models = "Available whisper models:  \n"
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    available_models,
                                    notice=True,
                                    event=event)

        return True

    @power_user_function
    @matrix_command
    async def _room(self, opts, matrix_room, event):
        """
        Usage:
          room get expert
          room set expert [<expert_name>]
          room unset expert
          room add user <matrix_user> <name>
          room rm user <matrix_user>
          room get users
          room set users
          room set echo (on|off)
          room set index-conversation (on|off)
        """
        if "echo" in opts and opts['echo']:
            flag = True if opts['on'] else False
            room().set_echo(matrix_room, flag)
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f"Flag `echo` is now {flag}",
                                    notice=True,
                                    event=event)
        if "index-conversation" in opts and opts['index-conversation']:
            flag = True if opts['on'] else False
            room().set_index_conversation(matrix_room, flag)
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f"Flag `index-conversation` is now {flag}",
                                    notice=True,
                                    event=event)

        elif 'users' in opts and opts['users']:
            if 'get' in opts and opts['get']:
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        json.dumps(
                                            room().get(matrix_room)['users'],
                                            skipkeys=True,
                                            allow_nan=True,
                                            indent=6),
                                        notice=True,
                                        event=event)
            elif 'set' in opts and opts['set']:
                room().set_users(matrix_room, room().get(matrix_room)['users'])
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        "Users mapping is now saved to the room!",
                                        notice=True,
                                        event=event)

        elif 'user' in opts and opts['user']:
            if 'add' in opts and opts['add']:
                room().get(matrix_room)['users'][
                    opts['<matrix_user>']] = opts['<name>']
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"user `{opts['<matrix_user>']}` is now mapped to `{opts['<name>']}`",
                                        notice=True,
                                        event=event)
            elif 'rm' in opts and opts['rm']:
                if opts['<matrix_user>'] in room().get(matrix_room)['users']:
                    del room().get(matrix_room)['users'][opts['<matrix_user>']]
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        f"User `{opts['<matrix_user>']}` has been removed from users mapping",
                        notice=True,
                        event=event)

        elif 'expert' in opts and opts['expert']:
            if 'get' in opts and opts['get']:
                if (room().get(matrix_room)['expert_id'] == -1):
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        "No expert is active yet, use the command `room set expert [<expert_name>]` to set one.",
                        notice=True,
                        event=event)
                else:
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        f"This room is using `{room().get(matrix_room)['expert_name']}` expert.",
                        room().get(matrix_room)['expert_name'],
                        event=event)
            elif 'unset' in opts and opts['unset']:
                if (room().get(matrix_room)['expert_id'] == -1):
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        "No expert is active yet, use the command `room set expert [<expert_name>]` to set one.",
                        event=event)
                else:
                    room().set_expert(matrix_room, -1)
                    await send_text_to_room(client(),
                                            matrix_room.room_id,
                                            f"Ok!",
                                            event=event)
            elif 'set' in opts and opts['set']:
                # if we have an expert name we fetch the ID from DB
                if '<expert_name>' in opts and opts['<expert_name>']:
                    with store().get_session() as session:
                        statement = select(Expert).filter(
                            Expert.name == opts['<expert_name>'])
                        # retrieve the expert from DB
                        expert = session.scalar(statement)
                        if expert is not None:
                            # and apply the expert
                            room().set_expert(matrix_room, expert.id)
                            await send_text_to_room(
                                client(),
                                matrix_room.room_id,
                                f"This room is now using the expert `{expert.name}[{expert.id}]`",
                                event=event)
                        else:
                            await send_text_to_room(client(),
                                                    matrix_room.room_id,
                                                    "Expert not found!",
                                                    event=event)
                elif (room().get(matrix_room)['expert_id'] != -1):
                    room().set_expert(matrix_room,
                                      room().get(matrix_room)['expert_id'])
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        f"This room is now using the expert `{room().get(matrix_room)['expert_name']}[{room().get(matrix_room)['expert_id']}]`",
                        event=event)
                else:
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        "No expert is active yet, use the command `room set expert [<expert_name>]` to set one - or specify an expert name.",
                        event=event)

        return True

    @power_user_function
    @matrix_command
    async def _expert(self, opts, matrix_room, event):
        """
        Usage:
          expert ls [<search>]
          expert save <expert_name> [<description>]
          expert load <expert_name>
          expert rm <expert_name>
          expert dump <expert_name>
        """
        if 'ls' in opts and opts['ls']:
            available_experts = "Saved experts:  \n"
            with store().get_session() as session:
                if '<search>' in opts and opts['<search>']:
                    statement = select(Expert).filter(
                        Expert.name.like(f"%{opts['<search>']}%"))
                else:
                    statement = select(Expert)
                for expert in session.scalars(statement):
                    available_experts += f"{expert.name}  \n"
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    available_experts,
                                    notice=True,
                                    event=event)

        elif 'save' in opts and opts['save']:
            with store().get_session() as session:
                description = ""
                if '<description>' in opts and opts['<description>']:
                    description = opts['<description>']
                new_expert = Expert(
                    name=opts['<expert_name>'],
                    description=description,
                    configuration=room().get(matrix_room)['client'].toJSON())
                session.add(new_expert)
                session.commit()

            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"Expert {opts['<expert_name>']} has been created!",
                notice=True,
                event=event)

        elif 'load' in opts and opts['load']:
            with store().get_session() as session:
                statement = select(Expert).filter(
                    Expert.name == opts['<expert_name>'])
                expert = session.scalar(statement)
                if expert is not None:
                    room().get(matrix_room)['client'].fromJSON(
                        expert.configuration)
                    room().get(matrix_room)['expert_id'] = expert.id
                    room().get(matrix_room)['expert_name'] = expert.name
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        f"Expert {opts['<expert_name>']} loaded, have fun!",
                        notice=True,
                        event=event)
                else:
                    await send_text_to_room(client(),
                                            matrix_room.room_id,
                                            "Expert not found!",
                                            notice=True,
                                            event=event)

        elif 'dump' in opts and opts['dump']:
            with store().get_session() as session:
                statement = select(Expert).filter(
                    Expert.name == opts['<expert_name>'])
                dumped_expert = session.scalar(statement)
                if dumped_expert is not None:
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        '"""\n' + dumped_expert.configuration + '\n"""',
                        notice=True,
                        event=event)
                else:
                    await send_text_to_room(client(),
                                            matrix_room.room_id,
                                            "Expert not found!",
                                            notice=True,
                                            event=event)

        elif 'rm' in opts and opts['rm']:
            with store().get_session() as session:
                stmt = select(Expert).filter(
                    Expert.name == opts['<expert_name>'])
                expert = session.scalar(stmt)
                if expert is not None:
                    # avoid the deletion of experts attached to the room
                    if expert.id == room().get(matrix_room)['expert_id']:
                        await send_text_to_room(
                            client(),
                            matrix_room.room_id,
                            "Cannot delete an expert which is attached to the current room",
                            notice=True,
                            event=event)
                        return True

                    session.delete(expert)
                    session.commit()
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        f"Expert {opts['<expert_name>']} deleted!",
                        notice=True,
                        event=event)
                else:
                    await send_text_to_room(client(),
                                            matrix_room.room_id,
                                            "Expert not found!",
                                            notice=True,
                                            event=event)

        return True
