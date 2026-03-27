# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Matrix BOB is a Matrix protocol bot that integrates LLMs, vector search (RAG), audio transcription, and image processing into Matrix chat rooms. It uses `matrix-nio` for the Matrix client, LlamaIndex + Qdrant for RAG, and an OpenAI-compatible API (e.g. Ollama) for LLM inference.

## Development Setup

```bash
# Install in editable mode
python -m venv .venv
source .venv/bin/activate
pip install --editable .

# Start required services (Qdrant + PostgreSQL + Adminer)
cd docker && docker-compose up -d

# Run database migrations
alembic upgrade head

# Start the bot
./bin/bob [config.yaml]
```

Config file defaults to `bin/config.yaml`. Use `bin/sample.config.yaml` as a template.

## Code Style

```bash
flake8 pawnai_bob/
isort pawnai_bob/
```

Flake8 ignores: W503, W504, E203, E731, E501. isort uses multi-line output mode 3 with trailing commas.

There are no automated tests.

## Architecture

### Global State (`pawnai_bob/globals.py`)

All major singletons are initialized in `init(config_file_path)` and accessed via getter functions (`settings()`, `config()`, `store()`, `client()`, `room_manager()`). These raise `NotInitializedError` if called before initialization. `config()` returns a flat dict of all bot configuration loaded from the PostgreSQL `BotConfiguration` table (not the YAML directly — YAML populates defaults at startup).

### Configuration System

Two-layer config:
1. **YAML** (`bin/config.yaml`) — minimal bootstrap: DB connection string, Matrix credentials to seed into DB
2. **Database** (`BotConfiguration` table) — runtime config as key-value pairs (e.g. `openai.default_model`, `matrix.command_prefix`). Accessed via `config().get('section.key')`. Use `utils/config.py` helpers (`get_value`, `set_value`, `get_config_dict`) for DB-level config access.

### Command Dispatch (`pawnai_bob/commands/`)

Commands flow: `SystemCommands` → `VisionCommands` → `ConversationCommands`. Each returns a truthy value if it handled the message. Commands use docopt-format docstrings parsed by the `@matrix_command` decorator. Power-user-only commands use `@power_user_function`.

`ConversationCommands` is the catch-all — it sends the message to the LLM chat engine.

### Room Configuration (`pawnai_bob/room.py`)

`Room` manages per-room state: assigned expert (LLM config preset), echo mode, index-conversation flag, vision two-step mode, and user display name mapping. Config is persisted to `RoomConfiguration` in PostgreSQL and cached in memory. Access via `room_manager().get(matrix_room)`.

### LLM Client (`pawnai_bob/openai_client.py`)

`OpenAIClient` wraps LlamaIndex with an OpenAI-compatible backend. It manages:
- LLM + embedding model initialization
- Qdrant vector store index (collection per room/expert)
- Chat engine (context mode or ReAct agent mode)
- `Expert` serialization (save/load named LLM configurations)

The client is lazily initialized and stored in the room's configuration dict.

### Event Flow

```
Matrix event → Callbacks (callbacks.py)
  ├── Text message → RoomListener.store_message_text → SystemCommands → VisionCommands → ConversationCommands
  ├── Audio        → RoomListener.transcribe_audio_message → AudioProcessor (Whisper) → command or index
  ├── Image        → RoomListener.describe_image → ImageProcessor (vision model) → index
  └── File         → RoomListener.store_file → LlamaIndex SimpleDirectoryReader → index
```

### Database Models (`pawnai_bob/models.py`)

- `Expert` — named LLM configurations (JSON-serialized `OpenAIClient` state)
- `RoomConfiguration` — per-room expert assignment + config blob
- `BotConfiguration` — global key-value config store
- `RoomMessage` — message history (room_id, author, text, timestamp)

Migrations are in `alembic/versions/`.

## Key Patterns

- **Async throughout**: All callbacks and processors are `async`. `nest_asyncio` is applied at startup to allow nested event loops.
- **Encrypted room support**: `matrix-nio[e2e]` handles E2EE. File downloads use `download_event_resources()` context manager which handles decryption and temp file cleanup.
- **Reply chains**: `get_related_reply_to_events()` in `utils/chat.py` recursively fetches reply chains to build conversation context.
- **Debug state**: Processing artifacts (transcriptions, vision descriptions, last error) are stored globally via `set_debug_*` and retrievable via `!bob debug` commands.
