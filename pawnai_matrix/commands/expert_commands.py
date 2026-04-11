from sqlalchemy import select

from pawnai_matrix.utils import send_text_to_room
from pawnai_matrix.utils.decorators import matrix_command, power_user_function
from pawnai_matrix import client, room, store
from pawnai_matrix.models import Expert


class ExpertCommands:

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
                    configuration=room().get_client(matrix_room).toJSON())
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
                    room().get_client(matrix_room).fromJSON(
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
                    if expert.id == room().get_expert_id(matrix_room):
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
