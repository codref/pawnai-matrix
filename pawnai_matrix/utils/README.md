# Matrix Bob Utilities

This package contains utility modules organized by functionality for better code organization and maintainability.

## Structure

```
pawnai_bob/utils/
├── __init__.py          # Package initialization with convenient imports
├── config.py            # Configuration management utilities
├── chat.py              # Chat and messaging helper functions
├── decorators.py        # Function decorators for commands
├── document.py          # Document data model
└── errors.py            # Custom exception classes
```

## Modules

### `config.py`
Configuration management utilities for working with BotConfiguration ORM model.

**Key Functions:**
- `get_default_configuration()` - Get default configuration values
- `populate_defaults()` - Populate database with defaults
- `populate_config_from_yaml()` - Import configuration from YAML file
- `get_config_dict()` - Load all configuration as dictionary
- `get_value()` / `set_value()` - Get/set individual configuration values
- `delete_config()` - Remove a configuration set
- `list_config_names()` - List all configuration names

**Usage:**
```python
from pawnai_bob.utils import populate_config_from_yaml, get_config_dict

# Import from YAML
with Session(engine) as session:
    populate_config_from_yaml(session, "config.yaml", config_name="production")
    session.commit()

# Load configuration
with Session(engine) as session:
    config = get_config_dict(session, "production")
```

### `chat.py`
Chat and messaging helper functions for Matrix interactions.

**Key Functions:**
- `send_text_to_room()` - Send text messages with markdown support
- `make_pill()` - Create user mention pills
- `react_to_event()` - Add reactions to messages
- `get_related_reply_to_events()` - Get reply chain
- `download_event_resources()` - Download event attachments

**Usage:**
```python
from pawnai_bob.utils import send_text_to_room, react_to_event

# Send a message
await send_text_to_room(client, room_id, "Hello!", notice=True)

# React to a message
await react_to_event(client, room_id, event_id, "👍")
```

### `decorators.py`
Function decorators for command methods.

**Decorators:**
- `@matrix_command` - Adds automatic docopt parsing to commands
- `@power_user_function` - Restricts commands to power users only

**Usage:**
```python
from pawnai_bob.utils import matrix_command, power_user_function

class MyCommands:
    @power_user_function
    @matrix_command
    async def _admin_command(self, opts, matrix_room, event):
        '''
        Admin-only command.
        
        Usage:
          admin [--option]
        '''
        # Implementation
        pass
```

### `document.py`
Simple document data model for storing text with metadata.

**Usage:**
```python
from pawnai_bob.utils import Document

doc = Document(
    text="Hello world",
    metadata={"author": "bob", "date": "2024-01-01"}
)
```

### `errors.py`
Custom exception classes.

**Classes:**
- `ConfigError` - Configuration-related errors

**Usage:**
```python
from pawnai_bob.utils import ConfigError

raise ConfigError("Invalid configuration value")
```

## Migration Guide

### Old Imports → New Imports

```python
# OLD
from pawnai_bob.config_utils import get_config_dict
from pawnai_bob.chat_functions import send_text_to_room
from pawnai_bob.document import Document
from pawnai_bob.errors import ConfigError

# NEW (recommended)
from pawnai_bob.utils import (
    get_config_dict,
    send_text_to_room,
    Document,
    ConfigError,
)

# OR (if you need many functions from one module)
from pawnai_bob.utils import config
from pawnai_bob.utils import chat

config_dict = config.get_config_dict(session)
await chat.send_text_to_room(client, room_id, message)
```

### Backward Compatibility

The old module names (`config_utils`, `chat_functions`, etc.) are still available for backward compatibility but are **deprecated**. They simply re-export from the new `utils` package.

## Benefits of New Organization

1. **Clear Separation of Concerns**: Related utilities are grouped together
2. **Better Discoverability**: Easy to find utilities by category
3. **Cleaner Imports**: Import multiple utilities from one package
4. **Scalability**: Easy to add new utility modules as the project grows
5. **Documentation**: Better structure for documenting utility functions

## Adding New Utilities

When adding new utility functions:

1. Determine the appropriate module (config, chat, etc.)
2. Add the function to that module
3. Export it in `__init__.py`
4. Update this README with usage examples

Example:
```python
# In utils/chat.py
def my_new_chat_helper():
    """Helper for chat operations."""
    pass

# In utils/__init__.py
from pawnai_bob.utils.chat import (
    ...,
    my_new_chat_helper,  # Add here
)

__all__ = [
    ...,
    "my_new_chat_helper",  # And here
]
```
