from pawnai_bob.utils import send_text_to_room
from pawnai_bob.utils.decorators import matrix_command, power_user_function
from pawnai_bob import client, room, config


class IndexCommands:

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
            for model_name in config().get('openai.llm_models', []):
                if model_name == room().get_client(matrix_room).llm_model:
                    available_models += f"**{model_name}**  \n"
                else:
                    available_models += f"{model_name}  \n"
            await send_text_to_room(client(),
                                    matrix_room.room_id,
                                    available_models,
                                    notice=True,
                                    event=event)

        elif 'set' in opts and opts['set']:
            room().get_client(matrix_room).set_llm_model(opts['<model_name>'])
            await send_text_to_room(
                client(),
                matrix_room.room_id,
                f"LLM is now {room().get_client(matrix_room).llm_model}",
                notice=True,
                event=event)
        return True
