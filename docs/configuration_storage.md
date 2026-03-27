# BotConfiguration Database Storage

This document explains the key-value based configuration storage system for matrix-bob using PostgreSQL and SQLAlchemy ORM.

## Overview

The `BotConfiguration` model stores configuration as key-value pairs in PostgreSQL, providing a flexible way to manage bot settings without requiring schema changes when adding new configuration options.

## Model Structure

### Table: `bot_configuration`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `config_name` | String(100) | Name of the configuration set (e.g., "default", "production") |
| `key` | String(255) | Configuration key (e.g., "openai_url") |
| `value` | Text | Configuration value (stored as string or JSON) |

**Indexes:**
- `config_name` - for efficient filtering by configuration set
- `key` - for quick lookups by configuration key

## Key Features

- **Multiple Configuration Sets**: Store different configurations (dev, staging, production) by name
- **Flexible Values**: Supports strings, numbers, lists, and dictionaries (stored as JSON)
- **Type Preservation**: Automatically serializes/deserializes JSON for complex types
- **Easy Updates**: No schema migrations needed when adding new configuration keys

## Usage Examples

### 1. Populate Database with Default Values

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pawnai_bob.models import Base
from pawnai_bob.config_utils import populate_defaults

# Create database and tables
engine = create_engine("postgresql://user:pass@localhost/dbname")
Base.metadata.create_all(engine)

# Populate with defaults
with Session(engine) as session:
    populate_defaults(session, config_name="default")
    session.commit()
```

Or use the provided script:

```bash
python scripts/populate_config_defaults.py default
```

### 2. Import Configuration from YAML

```python
from pawnai_bob.configuration import Configuration
from pawnai_bob.config_utils import populate_config_from_yaml

# Load YAML config
yaml_config = Configuration("config.yaml")

# Import to database
with Session(engine) as session:
    populate_config_from_yaml(session, yaml_config, config_name="production")
    session.commit()
```

Or use the provided script:

```bash
python scripts/import_yaml_config.py bin/config.yaml production
```

### 3. Read Configuration Values

#### Get all configuration as a dictionary:

```python
from pawnai_bob.config_utils import get_config_dict

with Session(engine) as session:
    config = get_config_dict(session, "production")
    print(f"OpenAI URL: {config['openai_url']}")
    print(f"LLM Models: {config['openai_llm_models']}")
```

#### Get individual values:

```python
from pawnai_bob.config_utils import get_value

with Session(engine) as session:
    url = get_value(session, "openai_url", "production")
    models = get_value(session, "openai_llm_models", "production")
```

#### Using the model directly:

```python
from pawnai_bob.models import BotConfiguration

with Session(engine) as session:
    value = BotConfiguration.get_value(session, "openai_url", "production")
```

### 4. Update Configuration Values

```python
from pawnai_bob.config_utils import set_value

with Session(engine) as session:
    # Update a string value
    set_value(session, "openai_url", "http://localhost:8080/v1", "default")
    
    # Update a list value (automatically serialized to JSON)
    set_value(session, "openai_llm_models", ["model1", "model2"], "default")
    
    session.commit()
```

### 5. Manage Multiple Configuration Sets

```python
from pawnai_bob.config_utils import list_config_names, delete_config

with Session(engine) as session:
    # List all configuration sets
    names = list_config_names(session)
    print(f"Available configs: {names}")
    
    # Delete a configuration set
    delete_config(session, "old_config")
    session.commit()
```

## Default Configuration Values

The system includes sensible defaults for all configuration keys. See `get_default_configuration()` in `config_utils.py` for the complete list.

Key defaults include:

- **Storage**: `./store`, `./tmp`, SQLite database
- **Qdrant**: `http://localhost:6333`
- **OpenAI**: `http://localhost:11434/v1` (Ollama default)
- **Vision**: Groq client with qwen2.5vl:7b model
- **Whisper**: Small model
- **Command Prefix**: `!c `

## Database Migration

To create the `bot_configuration` table in your database:

```bash
alembic upgrade head
```

This will apply the migration file:
```
alembic/versions/a1b2c3d4e5f6_added_bot_configuration_table.py
```

## Configuration Keys Reference

### Storage
- `store_path` - Path for persistent storage
- `temp_path` - Path for temporary files
- `database_connection_string` - SQLAlchemy database URL

### Qdrant (Vector Database)
- `qdrant_url` - Qdrant server URL
- `qdrant_default_collection_name` - Default collection name

### Whisper (Speech-to-Text)
- `whisper_default_model` - Default Whisper model
- `whisper_models` - Available Whisper models (list)

### AI Providers
- `huggingface_api_key` - HuggingFace API key
- `huggingface_inference_api_models_url` - HF inference API URL
- `groq_api_key` - Groq API key
- `nvidia_api_key` - NVIDIA API key
- `nvidia_inference_api_models_url` - NVIDIA API URL

### Vision (Image-to-Text)
- `vision_client` - Vision provider (groq, nvidia, etc.)
- `vision_default_itt_model` - Default image-to-text model
- `vision_models` - Available vision models (list)
- `vision_model_temperature` - Model temperature
- `vision_max_tokens` - Maximum tokens
- `vision_default_query` - Default vision prompt

### Image Generation (Text-to-Image)
- `image_generation_client` - Image generation provider
- `image_generation_default_tti_model` - Default text-to-image model
- `image_generation_models` - Available models (list)

### OpenAI / LLM
- `openai_url` - OpenAI-compatible API URL
- `openai_api_key` - API key
- `openai_default_model` - Default model
- `openai_default_llm_model` - Default LLM model
- `openai_llm_models` - Available LLM models (list)
- `openai_default_embed_model` - Default embedding model
- `openai_embed_models` - Available embedding models (list)
- `openai_default_prompt` - Default system prompt
- `openai_default_context_length` - Context length
- `openai_timeout` - API timeout
- `openai_default_chunk_size` - Default chunk size

### Tasks
- `tasks_path` - Path to task definitions

### Matrix
- `user_id` - Bot user ID (@bot:server.com)
- `user_password` - Bot password (optional if using token)
- `user_token` - Bot access token (optional if using password)
- `device_id` - Device ID
- `device_name` - Device name
- `homeserver_url` - Matrix homeserver URL
- `command_prefix` - Command prefix (e.g., "!c ")
- `inviters` - List of allowed inviters
- `power_users` - List of power users

## Scripts

### `scripts/demo_config_storage.py`
Demonstrates all features of the configuration storage system using an in-memory SQLite database.

```bash
python scripts/demo_config_storage.py
```

### `scripts/populate_config_defaults.py`
Populates the database with default configuration values.

```bash
python scripts/populate_config_defaults.py [config_name]
```

### `scripts/import_yaml_config.py`
Imports configuration from a YAML file to the database.

```bash
python scripts/import_yaml_config.py <yaml_file> [config_name]
```

## Advantages of Key-Value Storage

1. **Schema Flexibility**: Add new configuration options without database migrations
2. **Multiple Environments**: Easily manage dev, staging, production configs
3. **Dynamic Updates**: Change configuration at runtime without restarts
4. **Type Safe**: Automatic JSON serialization for complex types
5. **Simple Queries**: Easy to retrieve specific values or entire configuration sets
6. **Audit Trail**: Can easily extend to track configuration changes

## API Reference

See the complete API documentation in:
- `pawnai_bob/models.py` - `BotConfiguration` model
- `pawnai_bob/config_utils.py` - Helper functions
