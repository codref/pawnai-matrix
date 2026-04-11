import asyncio
import logging
import os
import tempfile
from pathlib import Path

from openai import APIStatusError, OpenAI
from nio import MatrixRoom, RoomSendError, UploadError

from pawnai_matrix import client, config, room, set_debug_tts_transcript
from pawnai_matrix.utils import send_text_to_room

log = logging.getLogger(__name__)

PREVIEW_LENGTH = 200

_FORMAT_CONTENT_TYPE = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "opus": "audio/ogg",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "pcm": "audio/pcm",
}


class TTSProcessor:

    @staticmethod
    def _fmt() -> str:
        return config().get("openai.tts_format") or "opus"

    def _synthesise(self, text: str, output_path: Path,
                    model: str, voice: str, language: str, fmt: str, speed: float) -> None:
        tts_client = OpenAI(
            base_url=config().get("openai.url", "http://localhost:4000"),
            api_key=config().get("openai.api_key") or "none",
        )
        try:
            resp = tts_client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format=fmt,
                speed=speed,
                extra_body={"language": language},
            )
        except APIStatusError as exc:
            raise RuntimeError(f"TTS API error: {exc}") from exc
        resp.write_to_file(output_path)

    @staticmethod
    def _make_preview(text: str) -> str:
        s = text.strip()
        return s if len(s) <= PREVIEW_LENGTH else s[:PREVIEW_LENGTH].rstrip() + "\u2026"

    async def process(self, matrix_room: MatrixRoom, event, response_text: str) -> None:
        if not response_text.strip():
            return

        model = (room().get_tts_model(matrix_room)
                 or config().get("openai.tts_model")
                 or "tts-1")
        voice = (room().get_tts_voice(matrix_room)
                 or config().get("openai.tts_voice")
                 or "af_heart")
        language = (room().get_tts_language(matrix_room)
                    or config().get("openai.tts_language")
                    or "en")
        fmt = self._fmt()
        speed = float(config().get("openai.tts_speed") or 1.0)
        content_type = _FORMAT_CONTENT_TYPE.get(fmt, "audio/ogg")
        filename = f"tts_response.{fmt}"

        temp_dir = tempfile.mkdtemp(dir=config().get("storage.temp_path", "./tmp"))
        audio_path = Path(temp_dir) / filename
        try:
            await asyncio.to_thread(
                self._synthesise, response_text, audio_path,
                model, voice, language, fmt, speed,
            )
            file_size = audio_path.stat().st_size

            with audio_path.open("rb") as fh:
                upload_resp, _ = await client().upload(
                    data_provider=fh,
                    content_type=content_type,
                    filename=filename,
                    filesize=file_size,
                )

            if isinstance(upload_resp, UploadError):
                raise RuntimeError(f"Matrix upload failed: {upload_resp.message}")

            audio_send = await client().room_send(
                matrix_room.room_id,
                "m.room.message",
                {
                    "msgtype": "m.audio",
                    "url": upload_resp.content_uri,
                    "body": filename,
                    "info": {"mimetype": content_type, "size": file_size},
                },
                ignore_unverified_devices=True,
            )

            if not isinstance(audio_send, RoomSendError):
                await send_text_to_room(
                    client(),
                    matrix_room.room_id,
                    self._make_preview(response_text),
                    notice=True,
                    reply_to_event_id=audio_send.event_id,
                )

            set_debug_tts_transcript(matrix_room.room_id, response_text)

        finally:
            try:
                if audio_path.exists():
                    os.remove(audio_path)
                os.rmdir(temp_dir)
            except OSError:
                log.warning("Could not clean up TTS temp dir %s", temp_dir)
