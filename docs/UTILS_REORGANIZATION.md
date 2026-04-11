# Utils Package Reorganization

## Overview

The utility files in Matrix Bob have been reorganized into a structured `utils` package for better maintainability and discoverability.

## New Structure

```
pawnai_matrix/
├── utils/                    # NEW: Organized utilities package
│   ├── __init__.py          # Convenient imports from all utils
│   ├── README.md            # Detailed utils documentation
│   ├── config.py            # Configuration management (was config_utils.py)
│   ├── chat.py              # Chat/messaging functions (was chat_functions.py)
│   ├── decorators.py        # Command decorators (extracted from commands)
│   ├── document.py          # Document data model
│   └── errors.py            # Custom exceptions
│
├── config_utils.py          # DEPRECATED: Backward compatibility wrapper
├── chat_functions.py        # DEPRECATED: Backward compatibility wrapper
├── document.py              # DEPRECATED: Backward compatibility wrapper
└── errors.py                # DEPRECATED: Backward compatibility wrapper
```

## Changes Made

### 1. Created `pawnai_matrix/utils/` Package

All utility modules are now organized under `pawnai_matrix/utils/`:

- **`config.py`**: Configuration management utilities (previously `config_utils.py`)
  - `get_default_configuration()`
  - `populate_defaults()`
  - `populate_config_from_yaml()`
  - `get_config_dict()`
  - `get_value()` / `set_value()`
  - `delete_config()`
  - `list_config_names()`

- **`chat.py`**: Chat and messaging helper functions (previously `chat_functions.py`)
  - `send_text_to_room()`
  - `make_pill()`
  - `react_to_event()`
  - `get_related_reply_to_events()`
  - `download_event_resources()`
  - And more...

- **`decorators.py`**: Command decorators (extracted from commands modules)
  - `@matrix_command` - Adds docopt parsing
  - `@power_user_function` - Restricts to power users

- **`document.py`**: Document data model
  - `Document` class

- **`errors.py`**: Custom exception classes
  - `ConfigError`

### 2. Backward Compatibility

The old module names are still available but **deprecated**:
- `pawnai_matrix.config_utils` → use `pawnai_matrix.utils.config`
- `pawnai_matrix.chat_functions` → use `pawnai_matrix.utils.chat`
- `pawnai_matrix.document` → use `pawnai_matrix.utils.document`
- `pawnai_matrix.errors` → use `pawnai_matrix.utils.errors`

These modules now show a `DeprecationWarning` and re-export from the new locations.

### 3. Convenient Imports

You can now import utilities in multiple ways:

```python
# Option 1: Import from utils package (recommended)
from pawnai_matrix.utils import (
    get_config_dict,
    send_text_to_room,
    Document,
    ConfigError,
    matrix_command,
)

# Option 2: Import from specific modules
from pawnai_matrix.utils.config import get_config_dict
from pawnai_matrix.utils.chat import send_text_to_room

# Option 3: Import modules
from pawnai_matrix.utils import config, chat
config_dict = config.get_config_dict(session)
await chat.send_text_to_room(client, room_id, message)

# Option 4: Backward compatible (deprecated, shows warning)
from pawnai_matrix.config_utils import get_config_dict
from pawnai_matrix.chat_functions import send_text_to_room
```

## Benefits

1. **Better Organization**: Related utilities are grouped together
2. **Clearer Intent**: Module names clearly indicate their purpose
3. **Easier Discovery**: Developers can find utilities by category
4. **Scalability**: Easy to add new utility modules
5. **Improved Documentation**: Structured documentation in utils/README.md
6. **Backward Compatible**: Existing code continues to work (with warnings)

## Migration Guide

### Updating Your Code

To migrate from the old structure to the new one:

**Before:**
```python
from pawnai_matrix.config_utils import populate_config_from_yaml, get_config_dict
from pawnai_matrix.chat_functions import send_text_to_room, react_to_event
from pawnai_matrix.document import Document
from pawnai_matrix.errors import ConfigError
```

**After:**
```python
from pawnai_matrix.utils import (
    populate_config_from_yaml,
    get_config_dict,
    send_text_to_room,
    react_to_event,
    Document,
    ConfigError,
)
```

### Updating Decorators in Commands

**Before:**
```python
# In commands/system_commands.py
def matrix_command(func):
    @functools.wraps(func)
    async def fn(self, args, matrix_room, event):
        # ... decorator logic
    return fn
```

**After:**
```python
from pawnai_matrix.utils import matrix_command, power_user_function

class SystemCommands:
    @power_user_function
    @matrix_command
    async def _admin_command(self, opts, matrix_room, event):
        # ...
```

## Files Modified

1. **Created:**
   - `pawnai_matrix/utils/__init__.py`
   - `pawnai_matrix/utils/README.md`
   - `pawnai_matrix/utils/config.py`
   - `pawnai_matrix/utils/chat.py`
   - `pawnai_matrix/utils/decorators.py`
   - `pawnai_matrix/utils/document.py`
   - `pawnai_matrix/utils/errors.py`

2. **Modified (backward compatibility wrappers):**
   - `pawnai_matrix/config_utils.py`
   - `pawnai_matrix/chat_functions.py`
   - `pawnai_matrix/document.py`
   - `pawnai_matrix/errors.py`

## Next Steps

### Recommended Actions

1. **Update imports gradually**: Start using `from pawnai_matrix.utils import ...` in new code
2. **Update decorators**: Modify command files to use `from pawnai_matrix.utils import matrix_command`
3. **Update existing files**: When touching existing files, update their imports
4. **Monitor deprecation warnings**: Check for deprecation warnings during development
5. **Remove old modules**: After all code is migrated, the old wrapper files can be removed

### Future Enhancements

- Add more specialized utility modules as needed (e.g., `utils/validation.py`, `utils/formatting.py`)
- Extract more common patterns from main modules
- Add comprehensive unit tests for utility functions
- Consider adding type stubs for better IDE support

## Documentation

See `pawnai_matrix/utils/README.md` for detailed documentation of each utility module and usage examples.
