# Audio Transcription Compatibility Plan

This document is a server-side compatibility checklist for the Matrix BOB audio transcription flow implemented in [pawnai_bob/processors/audio_processor.py](/home/operatore/git-codref/r-n-d/matrix-bob/pawnai_bob/processors/audio_processor.py).

Its purpose is to validate that the transcription server behind the OpenAI-compatible endpoint works with the current client code without requiring client-side changes.

## Scope

The client currently expects:

- an OpenAI-compatible `POST /v1/audio/transcriptions` endpoint
- multipart upload with `file` and `model`
- model name from `openai.audio_transcription_model` when set
- otherwise `openai.default_llm_model`
- otherwise `pawn-transcribe` as the final fallback
- a successful response that includes transcript text
- optional diarization fields that can be formatted as speaker turns

## Client Contract

The current client sends:

```python
model = (
    config().get("openai.audio_transcription_model")
    or config().get("openai.default_llm_model")
    or "pawn-transcribe"
)

response = audio_client.audio.transcriptions.create(
    model=model,
    file=file_handle,
    response_format="verbose_json",
)
```

Server compatibility requirements:

1. `POST /v1/audio/transcriptions` must exist.
2. The endpoint must accept multipart form uploads.
3. The `model` form field must accept the configured transcription model.
4. The `file` form field must accept the uploaded Matrix media file as-is.
5. The endpoint must accept `response_format=verbose_json`.
6. The response must provide usable transcript text.

## Minimum Response Requirements

At least one of the following must be present in the JSON response:

- top-level `text`
- top-level `transcript`
- `alternatives[].text`
- `alternatives[].transcript`

If none of those are returned, the client will fail the transcription.

## Diarization Compatibility

Diarization is optional but supported. The client recognizes these top-level arrays:

- `segments`
- `utterances`
- `diarization`
- `chunks`

Within each item, the client looks for speaker identity under any of:

- `speaker`
- `speaker_id`
- `speaker_label`
- `speaker_name`

Within each item, the client looks for text under any of:

- `text`
- `transcript`
- `alternatives[].text`
- `alternatives[].transcript`

Fallback diarization mode is also supported through top-level `words`, where each word may contain:

- `word`
- one of `speaker`, `speaker_id`, `speaker_label`, `speaker_name`

## Compatible Response Shapes

### Plain transcript only

```json
{
  "text": "hello this is a test transcription"
}
```

### Diarized segments

```json
{
  "text": "hello this is a test transcription",
  "segments": [
    {
      "speaker": "SPEAKER_00",
      "text": "hello"
    },
    {
      "speaker": "SPEAKER_01",
      "text": "this is a test transcription"
    }
  ]
}
```

### Diarization from words

```json
{
  "text": "hello this is a test transcription",
  "words": [
    {"word": "hello", "speaker": "SPEAKER_00"},
    {"word": "this", "speaker": "SPEAKER_01"},
    {"word": "is", "speaker": "SPEAKER_01"},
    {"word": "a", "speaker": "SPEAKER_01"},
    {"word": "test", "speaker": "SPEAKER_01"},
    {"word": "transcription", "speaker": "SPEAKER_01"}
  ]
}
```

## Incompatible Response Shapes

These will require either a server fix or a client parser update:

- transcript text only nested in an unsupported key
- diarization speaker labels only in a custom field not listed above
- non-JSON success response when `response_format=verbose_json` is requested
- streaming-only response with no final JSON body
- base64-wrapped payload instead of standard OpenAI-style JSON

## Server Verification Checklist

Run these checks on the transcription server:

1. Confirm `POST /v1/audio/transcriptions` is reachable.
2. Confirm authentication matches the configured `openai.api_key`.
3. Confirm the server accepts the configured transcription model.
4. Confirm the server accepts `.ogg` uploads from Matrix.
5. Confirm `response_format=verbose_json` returns JSON, not plain text.
6. Confirm the response always contains transcript text.
7. Confirm diarization is returned in one of the supported array formats if enabled.
8. Confirm speaker labels are stable and non-empty.
9. Confirm large files do not time out or exceed server-side body limits.
10. Confirm transcription failures return a readable JSON error message.

## Suggested curl Check

Replace the URL, token, and file path for your environment.

```bash
curl -X POST "$OPENAI_BASE_URL/audio/transcriptions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "model=$AUDIO_TRANSCRIPTION_MODEL" \
  -F "response_format=verbose_json" \
  -F "file=@/path/to/sample.ogg"
```

If your `OPENAI_BASE_URL` already ends with `/v1`, the final URL should be:

```text
$OPENAI_BASE_URL/audio/transcriptions
```

Example:

```text
http://localhost:4000/v1/audio/transcriptions
```

## Test Matrix

Use at least these cases:

1. Single-speaker short `.ogg` clip.
2. Two-speaker `.ogg` clip with clear turn-taking.
3. Audio containing a spoken command such as `c help`.
4. Empty or near-silent clip.
5. Corrupt or unsupported file upload.
6. Long clip near expected production size limits.

## Expected Client Behavior

If compatibility is correct:

- the bot reacts to the original event with `⏳`
- the transcript is posted back to the room
- the transcript is stored in the `room_message` table
- `!bob debug message` shows the last audio transcription
- spoken commands are routed through the existing command system

## Pass / Fail Template

Use this template while validating the server:

```text
Endpoint reachable: PASS/FAIL
Auth accepted: PASS/FAIL
Model accepted: PASS/FAIL
OGG accepted: PASS/FAIL
verbose_json returned: PASS/FAIL
Transcript text present: PASS/FAIL
Diarization present: PASS/FAIL
Speaker field compatible: PASS/FAIL
Word-level fallback compatible: PASS/FAIL
Command transcript compatible: PASS/FAIL
Large file compatible: PASS/FAIL
Error payload readable: PASS/FAIL
```

## If The Server Is Not Compatible

Preferred fixes on the server side:

1. Return top-level `text`.
2. Return diarization in `segments` with `speaker` and `text`.
3. Support `response_format=verbose_json`.
4. Keep the endpoint path and multipart contract fully OpenAI-compatible.

If the server cannot be changed, the fallback is to extend the client parser in [pawnai_bob/processors/audio_processor.py](/home/operatore/git-codref/r-n-d/matrix-bob/pawnai_bob/processors/audio_processor.py) to handle the actual response shape.
