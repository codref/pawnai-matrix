import logging

from nio import (
    InviteMemberEvent,
    JoinError,
    MatrixRoom,
    MegolmEvent,
    RoomGetEventError,
    RoomMessageText,
    UnknownEvent,
)

from pawnai_bob.commands import SystemCommands, ConversationCommands
from pawnai_bob.utils import make_pill, react_to_event, send_text_to_room, get_related_reply_to_events, get_reply_body, download_event_resources
from pawnai_bob import client, config, room
from pawnai_bob.listeners.room_listener import RoomListener

log = logging.getLogger(__name__)


class Callbacks:

    def __init__(self):
        self.command_prefix = config().get('matrix.command_prefix')
        self.system_commands = SystemCommands()
        self.conversation_commands = ConversationCommands()
        self.room_listener = RoomListener()

    @staticmethod
    def _is_message_edit_event(event: RoomMessageText) -> bool:
        source = getattr(event, "source", {}) or {}
        relation = source.get("content", {}).get("m.relates_to", {})
        return relation.get("rel_type") == "m.replace"

    def _normalize_message_text(self, event: RoomMessageText, message: str) -> tuple[str, bool]:
        if not self._is_message_edit_event(event):
            return message, False

        source = getattr(event, "source", {}) or {}
        new_body = source.get("content", {}).get("m.new_content", {}).get("body")
        if isinstance(new_body, str) and new_body.strip():
            return new_body, True

        if message.startswith("* "):
            return message[2:], True
        return message, True

    async def uploaded_file(self, matrix_room: MatrixRoom, event) -> None:
        """Callback for when a file event is received

        Args:
            matrix_room: The matrix_room the event came from.
            event: The event defining the message.
        """

        # Ignore messages from ourselves
        if event.sender == client().user:
            return        

        async with download_event_resources(event) as temp_path:
            if event.source["content"]["msgtype"] == "m.audio":
                await self.room_listener.transcribe_audio_message(
                    matrix_room, event, temp_path)
            else:
                await self.room_listener.store_file(matrix_room, event,
                                                    temp_path)

    async def message(self, matrix_room: MatrixRoom,
                      event: RoomMessageText) -> None:
        """Callback for when a message event is received

        Args:
            matrix_room: The matrix_room the event came from.

            event: The event defining the message.
        """
        # Extract the message text
        msg = event.body

        # Ignore messages from ourselves
        if event.sender == client().user:
            return

        # Process as message if in a public matrix_room without command prefix
        replies = await get_related_reply_to_events(client(), matrix_room,
                                                    event)
        if replies:
            msg = get_reply_body(event)
        msg, is_edited_event = self._normalize_message_text(event, msg)

        log.debug(
            f"Bot message received for matrix_room {matrix_room.display_name} | "
            f"{matrix_room.user_name(event.sender)}: {msg}")

        if msg.strip() == r"\reset":
            await self.system_commands.process("session reset", matrix_room, event)
            return

        # check for !bob commands in the beginning of the message
        has_command_prefix = msg.startswith(self.command_prefix)

        # matrix_room.is_group is often a DM, but not always.
        # matrix_room.is_group does not allow matrix_room aliases
        # matrix_room.member_count > 2 ... we assume a public matrix_room
        # matrix_room.member_count <= 2 ... we assume a DM
        # Otherwise if this is in a 1-1 with the bot or features a command prefix,
        # treat it as a command

        if has_command_prefix:
            # Remove the command prefix
            msg = msg[len(self.command_prefix):].lstrip()

            # Process commands
            if await self.system_commands.process(msg, matrix_room, event):
                return
            response = await self.conversation_commands.process(
                msg, matrix_room, event, replies)
            if response:
                if type(response) != str:
                    return

        else:
            free_speak = room().get_free_speak(matrix_room)
            if is_edited_event and not free_speak:
                await self.room_listener.store_message_text(
                    matrix_room,
                    event,
                    text_override=msg,
                )
            else:
                await self.room_listener.store_message_text(matrix_room, event)

            if free_speak:
                response = await self.conversation_commands.process(
                    msg, matrix_room, event, replies)
                if response:
                    if type(response) != str:
                        return

    async def invite(self, matrix_room: MatrixRoom,
                     event: InviteMemberEvent) -> None:
        """
        Callback for when an invite is received. Join the matrix_room specified in the invite.
        """
        log.debug(f"Got invite to {matrix_room.room_id} from {event.sender}.")

        # check for valid inviters
        inviters = config().get('matrix.inviters') or []
        if len(inviters) > 0 and matrix_room.inviter not in inviters:
            log.error(
                "Unable to join matrix_room: %s. The inviter %s is not allowed!",
                matrix_room.room_id, matrix_room.inviter)
            return

        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await client().join(matrix_room.room_id)
            if type(result) == JoinError:
                log.error(
                    f"Error joining matrix_room {matrix_room.room_id} (attempt %d): %s",
                    attempt,
                    result.message,
                )
            else:
                break
        else:
            log.error("Unable to join matrix_room: %s", matrix_room.room_id)

        # Successfully joined matrix_room
        log.info(f"Joined {matrix_room.room_id}")

    async def invite_event_filtered_callback(self, matrix_room: MatrixRoom,
                                             event: InviteMemberEvent) -> None:
        """
        Since the InviteMemberEvent is fired for every m.room.member state received
        in a sync response's `rooms.invite` section, we will receive some that are
        not actually our own invite event (such as the inviter's membership).
        This makes sure we only call `callbacks.invite` with our own invite events.
        """
        if event.state_key == client().user_id:
            # This is our own membership (invite) event
            await self.invite(matrix_room, event)

    async def _reaction(self, matrix_room: MatrixRoom, event: UnknownEvent,
                        reacted_to_id: str) -> None:
        """A reaction was sent to one of our messages. Let's send a reply acknowledging it.

        Args:
            matrix_room: The matrix_room the reaction was sent in.

            event: The reaction event.

            reacted_to_id: The event ID that the reaction points to.
        """
        log.debug(
            f"Got reaction to {matrix_room.room_id} from {event.sender}.")

        # Get the original event that was reacted to
        event_response = await client().room_get_event(matrix_room.room_id,
                                                       reacted_to_id)
        if isinstance(event_response, RoomGetEventError):
            log.warning("Error getting event that was reacted to (%s)",
                        reacted_to_id)
            return
        reacted_to_event = event_response.event

        # Only acknowledge reactions to events that we sent
        if reacted_to_event.sender != config().get('matrix.user_id'):
            return

        # Send a message acknowledging the reaction
        reaction_sender_pill = make_pill(event.sender)
        reaction_content = (event.source.get("content",
                                             {}).get("m.relates_to",
                                                     {}).get("key"))
        message = (
            f"{reaction_sender_pill} reacted to this event with `{reaction_content}`!"
        )
        await send_text_to_room(
            client(),
            matrix_room.room_id,
            message,
            reply_to_event_id=reacted_to_id,
        )

    async def decryption_failure(self, matrix_room: MatrixRoom,
                                 event: MegolmEvent) -> None:
        """Callback for when an event fails to decrypt. Inform the user.

        Args:
            matrix_room: The matrix_room that the event that we were unable to decrypt is in.

            event: The encrypted event that we were unable to decrypt.
        """
        log.error(
            f"Failed to decrypt event '{event.event_id}' in room '{matrix_room.room_id}'!"
            f"\n\n"
            f"Tip: try using a different device ID in your config file and restart."
            f"\n\n"
            f"If all else fails, delete your store directory and let the bot recreate "
            f"it (your reminders will NOT be deleted, but the bot may respond to existing "
            f"commands a second time).")

        red_x_and_lock_emoji = "❌ 🔐"

        # React to the undecryptable event with some emoji
        await react_to_event(
            client(),
            matrix_room.room_id,
            event.event_id,
            red_x_and_lock_emoji,
        )

    async def unknown(self, matrix_room: MatrixRoom,
                      event: UnknownEvent) -> None:
        """Callback for when an event with a type that is unknown to matrix-nio is received.
        Currently this is used for reaction events, which are not yet part of a released
        matrix spec (and are thus unknown to nio).

        Args:
            matrix_room: The matrix_room the reaction was sent in.

            event: The event itself.
        """
        if event.type == "m.reaction":
            # Get the ID of the event this was a reaction to
            relation_dict = event.source.get("content",
                                             {}).get("m.relates_to", {})

            reacted_to = relation_dict.get("event_id")
            if reacted_to and relation_dict.get("rel_type") == "m.annotation":
                await self._reaction(matrix_room, event, reacted_to)
                return

        log.debug(
            f"Got unknown event with type to {event.type} from {event.sender} in {matrix_room.room_id}."
        )
