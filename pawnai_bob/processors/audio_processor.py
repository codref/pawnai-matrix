import logging
import re
import arrow
import glob
from nio import MatrixRoom
from pawnai_bob.utils import send_text_to_room, react_to_event, Document
from pawnai_bob import client, room, config

log = logging.getLogger(__name__)


class AudioProcessor:
    """Process audio messages: transcribe and route to commands or indexing."""

    @staticmethod
    def _get_command_prefix() -> str:
        """Extract command prefix without special characters."""
        return re.sub(r'[^\w+]', '', config().get('matrix.command_prefix', ''))

    @staticmethod
    def _get_mapped_user(event, matrix_room: MatrixRoom) -> str:
        """Get user from mapping or return sender."""
        sender = event.source.get('sender')
        users = room().get_users(matrix_room)
        return users.get(sender, sender)

    @staticmethod
    def _is_command(text: str, prefix: str) -> bool:
        """Check if text starts with command prefix."""
        return text[:len(prefix) + 5].strip().lower().startswith(prefix)

    async def _process_audio_command(
        self, matrix_room: MatrixRoom, event, text: str
    ) -> None:
        """Handle audio input that starts with command prefix."""
        await client().room_typing(matrix_room.room_id, True, timeout=120000)
        response = room().get_client(matrix_room).chat_engine.chat(text)
        await client().room_typing(matrix_room.room_id, False)
        await send_text_to_room(
            client(), matrix_room.room_id, str(response), event=event
        )

    async def _index_audio_as_document(
        self, matrix_room: MatrixRoom, event, text: str
    ) -> None:
        """Index transcribed audio as a document."""
        sender = self._get_mapped_user(event, matrix_room)
        document = Document(
            text=text,
            metadata={
                "room": matrix_room.room_id,
                "author": sender,
                "date": arrow.utcnow().to('Europe/Rome').format('dddd, D of MMMM'),
            },
        )
        room().get_client(matrix_room).index_document([document])
        if room().get_echo(matrix_room):
            await send_text_to_room(client(), matrix_room.room_id, "ok", event=event)

    async def process(self, matrix_room: MatrixRoom, event, dir: str) -> None:
        """
        Transcribe audio files and route to commands or indexing.
        
        Args:
            matrix_room: The matrix room context
            event: The event that triggered the transcription
            dir: Directory containing audio files to transcribe
        """
        await react_to_event(
            client(), matrix_room.room_id, event.event_id, "⏳"
        )

        prefix = self._get_command_prefix()

        # TODO: manage multiple files in a better way
        for filepath in glob.iglob(f'{dir}/*.ogg'):
            # TODO: audio transcription not yet implemented
            log.warning("Audio transcription is not available; skipping %s", filepath)
