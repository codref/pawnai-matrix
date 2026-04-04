import logging
import os
import re
import tempfile
import aiofiles
import aiofiles.os
import glob
import base64
import mimetypes
from contextlib import asynccontextmanager
from typing import Optional, Union
from PIL import Image
import magic
from markdown import markdown
from nio import (AsyncClient, ErrorResponse, MatrixRoom, MegolmEvent, Response,
                 RoomSendResponse, SendRetryError, RoomMessageFile,
                 RoomMessageAudio, RoomEncryptedAudio, RoomMessageImage,
                 RoomEncryptedImage, RoomEncryptedFile, crypto, UploadResponse)


log = logging.getLogger(__name__)


async def send_text_to_room(
    client: AsyncClient,
    room_id: str,
    message: str,
    notice: bool = False,
    markdown_convert: bool = True,
    reply_to_event_id: Optional[str] = None,
    reply_to_thread_id: Optional[str] = None,
    event=None,
) -> Union[RoomSendResponse, ErrorResponse]:
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
        if event and "m.relates_to" in event.source['content'] and event.source[
                'content']['m.relates_to']['rel_type'] == "m.thread":
            reply_to_thread_id = event.source['content']['m.relates_to'][
                'event_id']
            reply_to_event_id = event.source['event_id']

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

async def send_image_to_room(client: AsyncClient, room_id: str, image):
    """
    Send image to room.
    Arguments:
    ---------
    client : Client
    room_id : str
    image : str, file name of image

    This is a working example for a JPG image.
        "content": {
            "body": "someimage.jpg",
            "info": {
                "size": 5420,
                "mimetype": "image/jpeg",
                "thumbnail_info": {
                    "w": 100,
                    "h": 100,
                    "mimetype": "image/jpeg",
                    "size": 2106
                },
                "w": 100,
                "h": 100,
                "thumbnail_url": "mxc://example.com/SomeStrangeThumbnailUriKey"
            },
            "msgtype": "m.image",
            "url": "mxc://example.com/SomeStrangeUriKey"
        }


    """

    mime_type = magic.from_file(image, mime=True)  # e.g. "image/jpeg"

    if not mime_type.startswith("image/"):
        log.error("Drop message because file does not have an image mime type.")
        return

    im = Image.open(image)
    (width, height) = im.size  # im.size returns (width,height) tuple

    # first do an upload of image, then send URI of upload to room
    file_stat = await aiofiles.os.stat(image)
    async with aiofiles.open(image, "r+b") as f:
        resp, decryption_keys = await client.upload(
            f,
            content_type=mime_type,  # application/pdf
            filename=os.path.basename(image),
            filesize=file_stat.st_size,
            encrypt=True,
        )

    if isinstance(resp, UploadResponse):
        log.info("Image was uploaded successfully to server.")
    else:
        await send_text_to_room(
            client,
            room_id,
            f"Failed to upload image. Failure response: {resp}"
        )        
        log.error(f"Failed to upload image. Failure response: {resp}")        

    content = {
        "body": os.path.basename(image),  # descriptive title
        "info": {
            "size": file_stat.st_size,
            "mimetype": mime_type,
            # "thumbnail_info": None,  # TODO
            "w": width,  # width in pixel
            "h": height,  # height in pixel
            # "thumbnail_url": None,  # TODO
        },
        "msgtype": "m.image",
        "url": resp.content_uri,
        "file": {
            "url": resp.content_uri,
            "key": decryption_keys["key"],
            "iv": decryption_keys["iv"],
            "hashes": decryption_keys["hashes"],
            "v": decryption_keys["v"],
        },
    }

    try:
        await client.room_send(room_id, message_type="m.room.message", content=content, ignore_unverified_devices=True)
    except SendRetryError:
        log.exception(f"Image send of file {image} failed. {room_id}")


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


async def decryption_failure(self, room: MatrixRoom,
                             event: MegolmEvent) -> None:
    """Callback for when an event fails to decrypt. Inform the user"""
    log.error(
        f"Failed to decrypt event '{event.event_id}' in room '{room.room_id}'!"
        f"\n\n"
        f"Tip: try using a different device ID in your config file and restart."
        f"\n\n"
        f"If all else fails, delete your store directory and let the bot recreate "
        f"it (your reminders will NOT be deleted, but the bot may respond to existing "
        f"commands a second time).")

    user_msg = (
        "Unable to decrypt this message. "
        "Check whether you've chosen to only encrypt to trusted devices.")

    await send_text_to_room(
        self.client,
        room.room_id,
        user_msg,
        reply_to_event_id=event.event_id,
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
    from pawnai_bob.globals import config, client

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

def get_image_url_from_path(path, pattern = "/*", allowed_extensions=[".png", ".jpg", ".jpeg"]):
    """
    Retrieves the first image matching the 
    """

    # TODO having multiple files in here is not very smart, manage this loop in a better way
    for filepath in glob.iglob(f"{path}/{pattern}"):
        image_extension =  os.path.splitext(filepath)[1]
        mime_type = mimetypes.guess_type(filepath)[0]
        if image_extension in allowed_extensions:
            with open(filepath, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("ascii")
                return f"data:{mime_type};base64,{encoded_image}"
        
    return None
