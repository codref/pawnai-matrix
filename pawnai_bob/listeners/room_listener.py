import logging
import re
import arrow
from functools import wraps
from datetime import datetime
from nio import MatrixRoom, RoomMessageText
from pawnai_bob.utils import send_text_to_room, react_to_event
from pawnai_bob import client, room, set_debug_message, store
from pawnai_bob.models import RoomMessage
from pawnai_bob.processors.audio_processor import AudioProcessor


log = logging.getLogger(__name__)


def handle_room_errors(error_message: str):
    """
    Decorator to handle room method errors and echo responses.
    Wraps async methods with error handling and echo feedback.
    
    Args:
        error_message: Message to display on error (will append the exception details)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract matrix_room from positional args (self, matrix_room, ...)
            if len(args) >= 2:
                matrix_room = args[1]
            else:
                matrix_room = kwargs.get('matrix_room')
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                await send_text_to_room(
                    client(), 
                    matrix_room.room_id, 
                    f"{error_message}\n{e}",
                    event=kwargs.get('event', args[2] if len(args) > 2 else None)
                )
                set_debug_message(f"{error_message}\n{e}")
        return wrapper
    return decorator

class RoomListener:
    """
    Listen for messages and index the received content.
    """

    def __init__(self, collection_name) -> None:
        self.collection_name = collection_name
        self.audio_processor = AudioProcessor()

    @handle_room_errors("Cannot process the message:")
    async def store_message_text(self, matrix_room: MatrixRoom, event: RoomMessageText):
        """
        Store messages sent to a room in the database
        """
        # Attempt the user mapping
        sender = event.source.get('sender')
        users = room().get_users(matrix_room)
        if sender in users:
            sender = users[sender]

        # Create and store the message in the database
        message = RoomMessage(
            room_id=matrix_room.room_id,
            author=sender,
            text=event.body,
            timestamp=datetime.utcnow(),
            message_metadata={
                "date": arrow.utcnow().to('Europe/Rome').format('dddd, D of MMMM')
            }
        )
        
        # Save to database
        session = store().get_session()
        try:
            session.add(message)
            session.commit()
        except Exception as db_error:
            session.rollback()
            raise db_error
        finally:
            session.close()

    @handle_room_errors("Cannot process the document:")
    async def store_file(self, matrix_room: MatrixRoom, event, dir):
        """
        Store files sent to a room
        """
        await send_text_to_room(client(), matrix_room.room_id, "File indexing is not available.", event=event)

    @handle_room_errors("Cannot process the audio:")
    async def transcribe_audio_message(self, matrix_room: MatrixRoom, event, dir):
        """
        Use OpenAI-Whisper to transcribe an audio message or an audio file 
        """
        await self.audio_processor.process(matrix_room, event, dir)