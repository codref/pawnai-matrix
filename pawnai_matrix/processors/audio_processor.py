import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import arrow
from nio import MatrixRoom
from openai import APIStatusError, OpenAI

from pawnai_bob import client, config, room, set_debug_message, store
from pawnai_bob.commands import ConversationCommands, SystemCommands
from pawnai_bob.models import RoomMessage
from pawnai_bob.utils import react_to_event, send_text_to_room

log = logging.getLogger(__name__)


class AudioProcessor:
    """Process audio messages: transcribe, diarize, and route the result."""

    def __init__(self) -> None:
        self._system_commands = SystemCommands()
        self._conversation_commands = ConversationCommands()

    @staticmethod
    def _get_command_prefix() -> str:
        """Extract the spoken command prefix from the configured Matrix prefix."""
        return re.sub(r"[^\w+]", "", config().get("matrix.command_prefix", ""))

    @staticmethod
    def _get_mapped_user(event, matrix_room: MatrixRoom) -> str:
        """Get the mapped user name for the event sender."""
        sender = event.source.get("sender")
        users = room().get_users(matrix_room)
        return users.get(sender, sender)

    @staticmethod
    def _iter_audio_files(directory: str) -> list[Path]:
        return sorted(path for path in Path(directory).iterdir() if path.is_file())

    @staticmethod
    def _response_to_dict(response: Any) -> dict[str, Any]:
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if isinstance(response, dict):
            return response
        return {}

    @staticmethod
    def _extract_text(candidate: Any) -> str:
        if isinstance(candidate, str):
            return candidate.strip()
        if isinstance(candidate, dict):
            if isinstance(candidate.get("text"), str):
                return candidate["text"].strip()
            if isinstance(candidate.get("transcript"), str):
                return candidate["transcript"].strip()
            alternatives = candidate.get("alternatives")
            if isinstance(alternatives, list):
                for alternative in alternatives:
                    text = AudioProcessor._extract_text(alternative)
                    if text:
                        return text
        return ""

    @staticmethod
    def _extract_speaker(segment: dict[str, Any]) -> str:
        for key in ("speaker", "speaker_id", "speaker_label", "speaker_name"):
            value = segment.get(key)
            if value not in (None, ""):
                return str(value)
        return ""

    def _extract_diarized_segments(
        self, payload: dict[str, Any]
    ) -> list[dict[str, str]]:
        candidates = []
        for key in ("segments", "utterances", "diarization", "chunks"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates = value
                break

        diarized_segments: list[dict[str, str]] = []
        for segment in candidates:
            if not isinstance(segment, dict):
                continue

            speaker = self._extract_speaker(segment)
            text = self._extract_text(segment)

            if not speaker and isinstance(segment.get("words"), list):
                words = [
                    word.get("word", "").strip()
                    for word in segment["words"]
                    if isinstance(word, dict) and word.get("word")
                ]
                if words:
                    text = text or " ".join(words).strip()
                for word in segment["words"]:
                    if isinstance(word, dict):
                        speaker = self._extract_speaker(word)
                        if speaker:
                            break

            if speaker and text:
                diarized_segments.append({"speaker": speaker, "text": text})

        if diarized_segments:
            merged_segments: list[dict[str, str]] = [diarized_segments[0]]
            for segment in diarized_segments[1:]:
                previous = merged_segments[-1]
                if previous["speaker"] == segment["speaker"]:
                    previous["text"] = f"{previous['text']} {segment['text']}".strip()
                else:
                    merged_segments.append(segment)
            return merged_segments

        words = payload.get("words")
        if not isinstance(words, list):
            return []

        merged_segments = []
        current_speaker = None
        current_words: list[str] = []
        for word in words:
            if not isinstance(word, dict):
                continue
            speaker = self._extract_speaker(word)
            token = word.get("word")
            if not speaker or not token:
                continue

            normalized_token = str(token).strip()
            if not normalized_token:
                continue

            if current_speaker == speaker:
                current_words.append(normalized_token)
                continue

            if current_speaker and current_words:
                merged_segments.append(
                    {
                        "speaker": current_speaker,
                        "text": " ".join(current_words).strip(),
                    }
                )

            current_speaker = speaker
            current_words = [normalized_token]

        if current_speaker and current_words:
            merged_segments.append(
                {"speaker": current_speaker, "text": " ".join(current_words).strip()}
            )

        return merged_segments

    def _format_transcript(self, payload: dict[str, Any], fallback_text: str) -> str:
        diarized_segments = self._extract_diarized_segments(payload)
        if diarized_segments:
            return "\n".join(
                f"{segment['speaker']}: {segment['text']}"
                for segment in diarized_segments
            )

        text = self._extract_text(payload)
        return text or fallback_text

    @staticmethod
    def _get_transcription_model() -> str:
        return (
            config().get("openai.audio_transcription_model")
            or config().get("openai.default_llm_model")
            or "pawn-transcribe"
        )

    @staticmethod
    def _rewrite_model_access_error(exc: APIStatusError, model: str) -> Exception:
        message = str(exc)
        if exc.status_code != 401 or "key not allowed to access model" not in message:
            return exc

        return PermissionError(
            "Configured transcription model "
            f"'{model}' is not accessible with the current API key. "
            "Set 'openai.audio_transcription_model' to an allowed model, or leave it "
            "unset so audio transcription falls back to 'openai.default_llm_model'."
        )

    def _transcribe_file(self, filepath: Path) -> str:
        audio_client = OpenAI(
            base_url=config().get("openai.url", "http://localhost:4000"),
            api_key=config().get("openai.api_key") or "none",
        )
        model = self._get_transcription_model()

        with filepath.open("rb") as file_handle:
            try:
                response = audio_client.audio.transcriptions.create(
                    model=model,
                    file=file_handle,
                    response_format="verbose_json",
                )
            except APIStatusError as exc:
                raise self._rewrite_model_access_error(exc, model) from exc

        payload = self._response_to_dict(response)
        fallback_text = getattr(response, "text", "") or self._extract_text(payload)
        transcript = self._format_transcript(payload, fallback_text)

        if not transcript:
            raise ValueError(f"No transcription text returned for {filepath.name}")

        return transcript.strip()

    @staticmethod
    def _command_candidate(text: str) -> str:
        normalized = text.strip()
        if not normalized:
            return normalized

        first_line = normalized.splitlines()[0].strip()
        return re.sub(r"^[A-Za-z][\w .-]{0,40}:\s+", "", first_line, count=1)

    @staticmethod
    def _strip_command_prefix(text: str) -> str:
        actual_prefix = (config().get("matrix.command_prefix", "") or "").strip()
        spoken_prefix = AudioProcessor._get_command_prefix().strip()
        normalized = AudioProcessor._command_candidate(text)

        for prefix in (actual_prefix, spoken_prefix):
            if not prefix:
                continue
            pattern = rf"^{re.escape(prefix)}(?:[\s:,-]+|$)"
            if re.match(pattern, normalized, flags=re.IGNORECASE):
                return re.sub(
                    pattern, "", normalized, count=1, flags=re.IGNORECASE
                ).strip()

        return normalized

    @staticmethod
    def _is_command(text: str) -> bool:
        actual_prefix = (config().get("matrix.command_prefix", "") or "").strip().lower()
        spoken_prefix = AudioProcessor._get_command_prefix().strip().lower()
        normalized = AudioProcessor._command_candidate(text).lower()

        for prefix in (actual_prefix, spoken_prefix):
            if not prefix:
                continue
            if re.match(rf"^{re.escape(prefix)}(?:[\s:,-]+|$)", normalized):
                return True

        return False

    async def _store_transcript(
        self, matrix_room: MatrixRoom, event, transcript: str
    ) -> None:
        message = RoomMessage(
            room_id=matrix_room.room_id,
            author=self._get_mapped_user(event, matrix_room),
            text=transcript,
            timestamp=datetime.utcnow(),
            message_metadata={
                "date": arrow.utcnow().to("Europe/Rome").format("dddd, D of MMMM"),
                "source": "audio_transcription",
                "event_id": getattr(event, "event_id", None),
            },
        )

        session = store().get_session()
        try:
            session.add(message)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def _publish_transcript(
        self, matrix_room: MatrixRoom, event, transcript: str
    ) -> None:
        await send_text_to_room(
            client(),
            matrix_room.room_id,
            f"Transcription:\n{transcript}",
            notice=True,
            event=event,
        )

    async def _route_transcript(
        self, matrix_room: MatrixRoom, event, transcript: str
    ) -> None:
        if self._is_command(transcript):
            command = self._strip_command_prefix(transcript)
            if not command:
                return

            if await self._system_commands.process(command, matrix_room, event):
                return

            await self._conversation_commands.process(command, matrix_room, event, [])
            return

        if not room().get_free_speak(matrix_room):
            return

        await self._conversation_commands.process(
            transcript.strip(), matrix_room, event, []
        )

    async def process(self, matrix_room: MatrixRoom, event, dir: str) -> None:
        """
        Transcribe audio files and route to commands or indexing.

        Args:
            matrix_room: The matrix room context
            event: The event that triggered the transcription
            dir: Directory containing audio files to transcribe
        """
        await react_to_event(client(), matrix_room.room_id, event.event_id, "⏳")

        audio_files = self._iter_audio_files(dir)
        if not audio_files:
            raise FileNotFoundError(f"No audio files found in {dir}")

        transcripts = []
        for filepath in audio_files:
            log.info("Transcribing audio file %s", filepath)
            transcript = await asyncio.to_thread(self._transcribe_file, filepath)
            transcripts.append(transcript)

        combined_transcript = "\n\n".join(transcripts).strip()
        set_debug_message(f"Audio transcription:\n{combined_transcript}")

        await self._store_transcript(matrix_room, event, combined_transcript)
        await self._publish_transcript(matrix_room, event, combined_transcript)
        await self._route_transcript(matrix_room, event, combined_transcript)
