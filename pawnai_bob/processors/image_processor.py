import logging
import arrow
from nio import MatrixRoom
from pawnai_bob.utils import send_text_to_room, react_to_event, get_image_url_from_path, Document
from pawnai_bob import client, room, settings, set_debug_vision

log = logging.getLogger(__name__)


class ImageProcessor:
    """Process image messages: query vision model and index results."""

    @staticmethod
    def _get_mapped_user(event, matrix_room: MatrixRoom) -> str:
        """Get user from mapping or return sender."""
        sender = event.source.get('sender')
        users = room().get_users(matrix_room)
        return users.get(sender, sender)

    async def process(self, matrix_room: MatrixRoom, event, temp_path: str) -> None:
        """
        Query image with vision model and index the result.
        
        Args:
            matrix_room: The matrix room context
            event: The event that triggered the image processing
            temp_path: Path to the temporary image file
        """
        await react_to_event(
            client(), matrix_room.room_id, event.event_id, "⏳"
        )
        
        try:
            # Send a start typing event, with a fixed timeout
            # TODO estimate the typing duration or stream back the reply!
            await client().room_typing(matrix_room.room_id, True, timeout=120000)

            image_url = get_image_url_from_path(temp_path)

            # return immediately with no error if the image is not supported
            if image_url is None:
                return

            result = room().get_vision_client(matrix_room).query_image(
                image_url, settings().vision_default_query
            )
            set_debug_vision(result)

            # Create document for indexing
            await self._index_image_result(matrix_room, event, result)

        finally:
            await client().room_typing(matrix_room.room_id, False)

    async def _index_image_result(
        self, matrix_room: MatrixRoom, event, result: str
    ) -> None:
        """Index the vision model's image description as a document."""
        sender = self._get_mapped_user(event, matrix_room)
        document = Document(
            text=result,
            metadata={
                "room": matrix_room.room_id,
                "author": sender,
                "type": "image",
                "date": arrow.utcnow().to('Europe/Rome').format('dddd, D of MMMM'),
            },
        )
        room().get_client(matrix_room).index_document([document])

        if room().get_echo(matrix_room):
            await send_text_to_room(client(), matrix_room.room_id, "ok", event=event)
