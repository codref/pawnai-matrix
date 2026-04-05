import json
from sqlalchemy import select

from pawnai_bob.utils import send_text_to_room
from pawnai_bob.utils.decorators import matrix_command, power_user_function
from pawnai_bob import client, room, store
from pawnai_bob.models import Expert


class RoomConfigCommands:

    @power_user_function
    @matrix_command
    async def _room(self, opts, matrix_room, event):
        """
        Usage:
          room get expert
          room get free-speak
          room set expert [<expert_name>]
          room set free-speak (on|off)
          room unset expert
          room add user <matrix_user> <name>
          room rm user <matrix_user>
          room get users
          room set users
          room set echo (on|off)
        """
        if "free-speak" in opts and opts['free-speak']:
            if 'get' in opts and opts['get']:
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"Flag `free-speak` is {room().get_free_speak(matrix_room)}",
                                        notice=True,
                                        event=event)
            elif 'set' in opts and opts['set']:
                flag = True if opts['on'] else False
                room().set_free_speak(matrix_room, flag)
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"Flag `free-speak` is now {flag}",
                                        notice=True,
                                        event=event)
        elif "echo" in opts and opts['echo']:
            flag = True if opts['on'] else False
            room().set_echo(matrix_room, flag)
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    f"Flag `echo` is now {flag}",
                                    notice=True,
                                    event=event)
        elif 'users' in opts and opts['users']:
            if 'get' in opts and opts['get']:
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        json.dumps(
                                            room().get_users(matrix_room),
                                            skipkeys=True,
                                            allow_nan=True,
                                            indent=6),
                                        notice=True,
                                        event=event)
            elif 'set' in opts and opts['set']:
                room().set_users(matrix_room, room().get_users(matrix_room))
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        "Users mapping is now saved to the room!",
                                        notice=True,
                                        event=event)

        elif 'user' in opts and opts['user']:
            if 'add' in opts and opts['add']:
                room().get_users(matrix_room)[
                    opts['<matrix_user>']] = opts['<name>']
                await send_text_to_room(client(),
                                        matrix_room.room_id,
                                        f"user `{opts['<matrix_user>']}` is now mapped to `{opts['<name>']}`",
                                        notice=True,
                                        event=event)
            elif 'rm' in opts and opts['rm']:
                if opts['<matrix_user>'] in room().get_users(matrix_room):
                    del room().get_users(matrix_room)[opts['<matrix_user>']]
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        f"User `{opts['<matrix_user>']}` has been removed from users mapping",
                        notice=True,
                        event=event)

        elif 'expert' in opts and opts['expert']:
            if 'get' in opts and opts['get']:
                if (room().get_expert_id(matrix_room) == -1):
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
                        f"This room is using `{room().get_expert_name(matrix_room)}` expert.",
                        room().get_expert_name(matrix_room),
                        event=event)
            elif 'unset' in opts and opts['unset']:
                if (room().get_expert_id(matrix_room) == -1):
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
                elif (room().get_expert_id(matrix_room) != -1):
                    room().set_expert(matrix_room,
                                      room().get_expert_id(matrix_room))
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        f"This room is now using the expert `{room().get_expert_name(matrix_room)}[{room().get_expert_id(matrix_room)}]`",
                        event=event)
                else:
                    await send_text_to_room(
                        client(),
                        matrix_room.room_id,
                        "No expert is active yet, use the command `room set expert [<expert_name>]` to set one - or specify an expert name.",
                        event=event)

        return True
