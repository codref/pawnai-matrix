# Utils Package - Quick Reference

## Import Cheat Sheet

### All-in-One Import (Recommended)
```python
from pawnai_bob.utils import (
    # Config utilities
    get_config_dict,
    populate_config_from_yaml,
    get_value,
    set_value,
    
    # Chat utilities
    send_text_to_room,
    react_to_event,
    
    # Decorators
    matrix_command,
    power_user_function,
    
    # Models & Errors
    Document,
    ConfigError,
)
```

### By Module
```python
from pawnai_bob.utils.config import get_config_dict, populate_config_from_yaml
from pawnai_bob.utils.chat import send_text_to_room, react_to_event
from pawnai_bob.utils.decorators import matrix_command, power_user_function
from pawnai_bob.utils.document import Document
from pawnai_bob.utils.errors import ConfigError
```

### Import Entire Module
```python
from pawnai_bob.utils import config, chat

# Use as:
config_dict = config.get_config_dict(session)
await chat.send_text_to_room(client, room_id, message)
```

## Common Patterns

### Configuration Management
```python
from pawnai_bob.utils import get_config_dict, set_value

# Load configuration
with Session(engine) as session:
    config = get_config_dict(session, "production")
    
# Update configuration
with Session(engine) as session:
    set_value(session, "openai.url", "http://localhost:11434/v1")
    session.commit()
```

### Sending Messages
```python
from pawnai_bob.utils import send_text_to_room, react_to_event

# Send text
await send_text_to_room(client, room_id, "Hello!", notice=True)

# Add reaction
await react_to_event(client, room_id, event_id, "👍")
```

### Creating Commands
```python
from pawnai_bob.utils import matrix_command, power_user_function

class MyCommands:
    @matrix_command
    async def _public_command(self, opts, matrix_room, event):
        '''
        Public command available to all users.
        
        Usage:
          public_command [--flag]
        '''
        # Implementation
        
    @power_user_function
    @matrix_command
    async def _admin_command(self, opts, matrix_room, event):
        '''
        Admin command for power users only.
        
        Usage:
          admin_command <arg>
        '''
        # Implementation
```

## Module Contents

### `utils.config`
- `get_default_configuration()` - Get default config values
- `populate_defaults(session, config_name)` - Populate DB with defaults
- `populate_config_from_yaml(session, yaml_path, config_name)` - Import from YAML
- `get_config_dict(session, config_name)` - Load all config as dict
- `get_value(session, key, config_name, default)` - Get single value
- `set_value(session, key, value, config_name)` - Set single value
- `delete_config(session, config_name)` - Delete configuration
- `list_config_names(session)` - List all config names

### `utils.chat`
- `send_text_to_room(client, room_id, message, ...)` - Send text message
- `send_image_to_room(client, room_id, image)` - Send image
- `make_pill(user_id, displayname)` - Create user mention
- `react_to_event(client, room_id, event_id, reaction)` - Add reaction
- `get_related_reply_to_events(client, room, event)` - Get reply chain
- `get_reply_body(event)` - Extract reply content
- `concat_replies_body(events)` - Concatenate reply bodies
- `download_event_resources(event)` - Download event attachments
- `get_image_url_from_path(path)` - Get image URL from path

### `utils.decorators`
- `@matrix_command` - Add docopt parsing to commands
- `@power_user_function` - Restrict to power users

### `utils.document`
- `Document(text, metadata)` - Document class for indexing

### `utils.errors`
- `ConfigError` - Configuration error exception

## Migration Examples

### Example 1: Update a Command File
**Before:**
```python
# commands/system_commands.py
from pawnai_bob.chat_functions import send_text_to_room
from pawnai_bob import client

def matrix_command(func):
    # decorator implementation
    pass

class SystemCommands:
    @matrix_command
    async def _help(self, opts, matrix_room, event):
        await send_text_to_room(client(), matrix_room.room_id, "Help text")
```

**After:**
```python
# commands/system_commands.py
from pawnai_bob.utils import send_text_to_room, matrix_command
from pawnai_bob import client

class SystemCommands:
    @matrix_command
    async def _help(self, opts, matrix_room, event):
        await send_text_to_room(client(), matrix_room.room_id, "Help text")
```

### Example 2: Update a Listener
**Before:**
```python
# listeners/room_listener.py
from pawnai_bob.document import Document
from pawnai_bob.chat_functions import send_text_to_room, react_to_event

class RoomListener:
    async def handle_message(self, event):
        doc = Document(text="...", metadata={})
        await react_to_event(client, room_id, event_id, "✅")
```

**After:**
```python
# listeners/room_listener.py
from pawnai_bob.utils import Document, send_text_to_room, react_to_event

class RoomListener:
    async def handle_message(self, event):
        doc = Document(text="...", metadata={})
        await react_to_event(client, room_id, event_id, "✅")
```

### Example 3: Update a Script
**Before:**
```python
# scripts/import_yaml_config.py
from pawnai_bob.config_utils import populate_config_from_yaml, get_config_dict

with Session(engine) as session:
    populate_config_from_yaml(session, "config.yaml", "production")
    config = get_config_dict(session, "production")
```

**After:**
```python
# scripts/import_yaml_config.py
from pawnai_bob.utils import populate_config_from_yaml, get_config_dict

with Session(engine) as session:
    populate_config_from_yaml(session, "config.yaml", "production")
    config = get_config_dict(session, "production")
```

## Backward Compatibility

Old imports still work but show deprecation warnings:

```python
# These still work (with warnings):
from pawnai_bob.config_utils import get_config_dict  # DeprecationWarning
from pawnai_bob.chat_functions import send_text_to_room  # DeprecationWarning
from pawnai_bob.document import Document  # DeprecationWarning
from pawnai_bob.errors import ConfigError  # DeprecationWarning

# Update to these:
from pawnai_bob.utils import get_config_dict
from pawnai_bob.utils import send_text_to_room
from pawnai_bob.utils import Document
from pawnai_bob.utils import ConfigError
```

## Testing

```python
# Test imports
from pawnai_bob.utils import (
    get_config_dict,
    send_text_to_room,
    matrix_command,
    Document,
    ConfigError,
)

# Verify they're callable/usable
assert callable(get_config_dict)
assert callable(send_text_to_room)
assert callable(matrix_command)
assert Document("test") is not None
assert issubclass(ConfigError, Exception)
```

## See Also

- `pawnai_bob/utils/README.md` - Detailed documentation
- `docs/UTILS_REORGANIZATION.md` - Complete reorganization guide
- `docs/UTILS_ORGANIZATION_DIAGRAM.md` - Visual structure diagrams
