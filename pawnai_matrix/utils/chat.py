import logging
import re
import tempfile
import aiofiles
from contextlib import asynccontextmanager
from typing import Optional, Union
from markdown import markdown
from nio import (AsyncClient, ErrorResponse, MatrixRoom, MegolmEvent, Response,
                 RoomSendResponse, SendRetryError, RoomMessageFile,
                 RoomMessageAudio, RoomEncryptedAudio, RoomMessageImage,
                 RoomEncryptedImage, RoomEncryptedFile, crypto)


log = logging.getLogger(__name__)
LISTEN_ONLY_BYPASS_TOKEN = "PAWN_LISTEN_ONLY_BYPASS"


async def send_text_to_room(
    client: AsyncClient,
    room_id: str,
    message: str,
    notice: bool = False,
    markdown_convert: bool = True,
    reply_to_event_id: Optional[str] = None,
    reply_to_thread_id: Optional[str] = None,
    event=None,
) -> Union[RoomSendResponse, ErrorResponse, None]:
    """Send text to a matrix room.

    Args:
        client: The client to communicate to matrix with.

        room_id: The ID of the room to send the message to.

        message: The message content.

        notice: Whether the message should be sent with an "m.notice" message type
            (will not ping users).

        markdown_convert: Whether to convert the message content to markdown.
            Defaults to true.

        reply_to_event_id: Whether this message is a reply to another event. The event
            ID this is message is a reply to.

    Returns:
        A RoomSendResponse if the request was successful, else an ErrorResponse.
    """
    if LISTEN_ONLY_BYPASS_TOKEN in message:
        log.info(
            "Skipping outbound Matrix message because listen-only bypass token was detected."
        )
        return None

    # Determine whether to ping room members or not
    msgtype = "m.notice" if notice else "m.text"

    content = {
        "msgtype": msgtype,
        "format": "org.matrix.custom.html",
        "body": message,
    }

    if markdown_convert:
        content["formatted_body"] = markdown(message,
                                             extensions=['fenced_code'])

    try:
        if event:
            thread_root_event_id = get_thread_root_event_id(event)
            if thread_root_event_id:
                reply_to_thread_id = thread_root_event_id
                reply_to_event_id = getattr(event, "event_id", None) or event.source.get(
                    "event_id"
                )

        # reply to thread
        if reply_to_thread_id:
            replied_event_id = reply_to_thread_id if reply_to_event_id is None else reply_to_event_id
            content["m.relates_to"] = {
                "rel_type": "m.thread",
                "event_id": reply_to_thread_id,
                "is_falling_back": True,
                "m.in_reply_to": {
                    "event_id": replied_event_id
                }
            }
        elif reply_to_event_id:
            content["m.relates_to"] = {
                "m.in_reply_to": {
                    "event_id": reply_to_event_id
                }
            }
    except Exception:
        log.error("Cannot fully process the nested message")

    try:
        return await client.room_send(
            room_id,
            "m.room.message",
            content,
            ignore_unverified_devices=True,
        )
    except SendRetryError:
        log.exception(f"Unable to send message response to {room_id}")

def make_pill(user_id: str, displayname: str = None) -> str:
    """Convert a user ID (and optionally a display name) to a formatted user 'pill'

    Args:
        user_id: The MXID of the user.

        displayname: An optional displayname. Clients like Element will figure out the
            correct display name no matter what, but other clients may not. If not
            provided, the MXID will be used instead.

    Returns:
        The formatted user pill.
    """
    if not displayname:
        # Use the user ID as the displayname if not provided
        displayname = user_id

    return f'<a href="https://matrix.to/#/{user_id}">{displayname}</a>'


async def react_to_event(
    client: AsyncClient,
    room_id: str,
    event_id: str,
    reaction_text: str,
) -> Union[Response, ErrorResponse]:
    """Reacts to a given event in a room with the given reaction text

    Args:
        client: The client to communicate to matrix with.

        room_id: The ID of the room to send the message to.

        event_id: The ID of the event to react to.

        reaction_text: The string to react with. Can also be (one or more) emoji characters.

    Returns:
        A nio.Response or nio.ErrorResponse if an error occurred.

    Raises:
        SendRetryError: If the reaction was unable to be sent.
    """
    content = {
        "m.relates_to": {
            "rel_type": "m.annotation",
            "event_id": event_id,
            "key": reaction_text,
        }
    }

    return await client.room_send(
        room_id,
        "m.reaction",
        content,
        ignore_unverified_devices=True,
    )


async def get_related_reply_to_events(client: AsyncClient,
                                      room: MatrixRoom,
                                      event,
                                      events=None):
    """Returns an array containing all the replied events related"""
    if events is None:  #must use sentinel value in here https://docs.quantifiedcode.com/python-anti-patterns/correctness/mutable_default_value_as_argument.html#use-a-sentinel-value-to-denote-an-empty-list-or-dictionary
        events = []
    if _is_reply_message(event):
        reply_to_event_id = event.source['content']['m.relates_to'][
            'm.in_reply_to']['event_id']
        related_event = await client.room_get_event(room.room_id,
                                                    reply_to_event_id)
        events.append(related_event.event)
        return await get_related_reply_to_events(client, room,
                                                 related_event.event, events)
    else:
        return events


def get_reply_body(event):
    if hasattr(event, "formatted_body") and event.formatted_body is not None:
        result = re.search(r"<\/mx-reply>(.*)", event.formatted_body)
        return result[1] if result is not None else event.body
    else:
        if hasattr(event, "body"):
            return event.body
        else:
            return ""


def get_thread_root_event_id(event) -> Optional[str]:
    """Return the Matrix thread root event ID for a threaded event."""
    source = getattr(event, "source", {}) or {}
    content = source.get("content", {}) or {}
    relates_to = content.get("m.relates_to", {}) or {}

    if relates_to.get("rel_type") != "m.thread":
        return None

    event_id = relates_to.get("event_id")
    if isinstance(event_id, str) and event_id:
        return event_id
    return None



def _is_reply_message(event: MegolmEvent):
    return hasattr(event, 'source') and "m.relates_to" in event.source[
        'content'] and "m.in_reply_to" in event.source['content'][
            'm.relates_to']

@asynccontextmanager
async def download_event_resources(event):
    """
        Creates a temporary directory and downloads on it the 
        file associated to the event object passed
    """
    from pawnai_matrix.globals import config, client

    temp_path_instance = tempfile.TemporaryDirectory(
        dir=config().get("storage.temp_path", "./tmp"), ignore_cleanup_errors=True)
    temp_path = temp_path_instance.name
    try:
        log.debug(f"Created temporary directory {temp_path}")
        #TODO sanitize file name
        #TODO catch errors
        if (isinstance(event, RoomMessageFile)
                or isinstance(event, RoomMessageAudio)
                or isinstance(event, RoomMessageImage)):
            log.info(f"Received file {event.body} [{event.url}]")
            result = await client().download(
                mxc=event.url, save_to=f"{temp_path}/{event.body}")
        elif (isinstance(event, RoomEncryptedFile)
              or isinstance(event, RoomEncryptedAudio)
              or isinstance(event, RoomEncryptedImage)):
            log.info(f"Received encrypted file {event.body} [{event.url}]")
            encrypted_file = await client().download(mxc=event.url)
            filename = f"{temp_path}/{event.body}"
            async with aiofiles.open(filename, "wb") as f:
                await f.write(
                    crypto.attachments.decrypt_attachment(
                        encrypted_file.body,
                        event.source["content"]["file"]["key"]["k"],
                        event.source["content"]["file"]["hashes"]["sha256"],
                        event.source["content"]["file"]["iv"],
                    ))
        yield temp_path
    finally:
        temp_path_instance.cleanup()
