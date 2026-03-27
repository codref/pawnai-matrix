import logging
import re
import arrow
import nest_asyncio
import glob
import base64
from functools import wraps
from datetime import datetime
from nio import MatrixRoom, RoomMessageText
from pawnai_bob.utils import send_text_to_room, react_to_event, get_image_url_from_path
from pawnai_bob import client, room, g, settings, set_debug_message, set_debug_vision, set_debug_whispered, store
from pawnai_bob.utils import Document
from pawnai_bob.models import RoomMessage
from pawnai_bob.processors.audio_processor import AudioProcessor
from pawnai_bob.processors.image_processor import ImageProcessor


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
        self.image_processor = ImageProcessor()

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

        # React with a hourglass emoji
        await react_to_event(
            client(), matrix_room.room_id, event.event_id, "⏳"
        )
        
        nest_asyncio.apply()
        reader = SimpleDirectoryReader(
            input_dir=dir
        )
        
        documents = await reader.aload_data()
        await send_text_to_room(client(), matrix_room.room_id, f"Indexing {len(documents)} documents...", event=event)
        room().get_client(matrix_room).index_document(documents)
        await send_text_to_room(client(), matrix_room.room_id, f"Done indexing all the documents!", event=event)         

    @handle_room_errors("Cannot process the image:")
    async def describe_image(self, matrix_room: MatrixRoom, event, temp_path):
        """
        Query image with vision model and index the result
        """
        await self.image_processor.process(matrix_room, event, temp_path)
            

    @handle_room_errors("Cannot process the audio:")
    async def transcribe_audio_message(self, matrix_room: MatrixRoom, event, dir):
        """
        Use OpenAI-Whisper to transcribe an audio message or an audio file 
        """
        await self.audio_processor.process(matrix_room, event, dir)