# Matrix Bob - Utils Package Organization

## Before (Old Structure)

```
pawnai_bob/
├── __init__.py
├── app.py
├── callbacks.py
├── config_utils.py         ← Utility functions scattered
├── chat_functions.py       ← Utility functions scattered
├── document.py             ← Data model at root level
├── errors.py               ← Custom exceptions at root level
├── configuration.py
├── globals.py
├── models.py
├── openai_client.py
├── room.py
├── storage.py
├── task.py
├── commands/
│   ├── __init__.py
│   ├── system_commands.py  ← Contains decorators mixed with commands
│   ├── conversation_commands.py
│   └── vision_commands.py
└── listeners/
    ├── __init__.py
    └── room_listener.py
```

## After (New Structure)

```
pawnai_bob/
├── __init__.py
├── app.py
├── callbacks.py
├── configuration.py
├── globals.py
├── models.py
├── openai_client.py
├── room.py
├── storage.py
├── task.py
│
├── utils/                         ← NEW: Organized utilities package
│   ├── __init__.py               ← Convenient imports
│   ├── README.md                 ← Documentation
│   ├── config.py                 ← Configuration utilities
│   ├── chat.py                   ← Chat/messaging functions
│   ├── decorators.py             ← Command decorators (extracted)
│   ├── document.py               ← Document data model
│   └── errors.py                 ← Custom exceptions
│
├── commands/
│   ├── __init__.py
│   ├── system_commands.py        ← Uses decorators from utils
│   ├── conversation_commands.py
│   └── vision_commands.py
│
├── listeners/
│   ├── __init__.py
│   └── room_listener.py
│
└── [backward compatibility wrappers]
    ├── config_utils.py           ← Deprecated, imports from utils.config
    ├── chat_functions.py         ← Deprecated, imports from utils.chat
    ├── document.py               ← Deprecated, imports from utils.document
    └── errors.py                 ← Deprecated, imports from utils.errors
```

## Import Examples

### Configuration Utils

**Old Way:**
```python
from pawnai_bob.config_utils import get_config_dict, populate_config_from_yaml
```

**New Way:**
```python
from pawnai_bob.utils import get_config_dict, populate_config_from_yaml
# OR
from pawnai_bob.utils.config import get_config_dict, populate_config_from_yaml
```

### Chat Functions

**Old Way:**
```python
from pawnai_bob.chat_functions import send_text_to_room, react_to_event
```

**New Way:**
```python
from pawnai_bob.utils import send_text_to_room, react_to_event
# OR
from pawnai_bob.utils.chat import send_text_to_room, react_to_event
```

### Decorators

**Old Way:**
```python
# Decorators were defined directly in system_commands.py
def matrix_command(func):
    # decorator code...
```

**New Way:**
```python
from pawnai_bob.utils import matrix_command, power_user_function

class MyCommands:
    @power_user_function
    @matrix_command
    async def _my_command(self, opts, matrix_room, event):
        # command implementation
```

### Document and Errors

**Old Way:**
```python
from pawnai_bob.document import Document
from pawnai_bob.errors import ConfigError
```

**New Way:**
```python
from pawnai_bob.utils import Document, ConfigError
# OR
from pawnai_bob.utils.document import Document
from pawnai_bob.utils.errors import ConfigError
```

## Benefits of New Structure

### 1. **Clear Separation of Concerns**
- Core business logic: `app.py`, `callbacks.py`, `configuration.py`, etc.
- Utility functions: `utils/` package
- Commands: `commands/` package
- Listeners: `listeners/` package

### 2. **Better Discoverability**
```python
# It's now obvious where to find utilities
from pawnai_bob.utils import ...  # All utilities here!

# vs. the old way
from pawnai_bob.config_utils import ...  # Which module has what I need?
from pawnai_bob.chat_functions import ...
from pawnai_bob.document import ...
```

### 3. **Scalability**
Adding new utilities is straightforward:
```
utils/
├── config.py
├── chat.py
├── decorators.py
├── validation.py      ← NEW: Add validation utilities
├── formatting.py      ← NEW: Add formatting utilities
└── network.py         ← NEW: Add network utilities
```

### 4. **Reduced Code Duplication**
Decorators are now shared across all command modules instead of being duplicated.

### 5. **Improved Documentation**
- `utils/README.md` provides comprehensive documentation
- Each module has a clear, single responsibility
- Examples are easier to write and understand

## File Organization Summary

| Category | Files | Purpose |
|----------|-------|---------|
| **Core** | `app.py`, `callbacks.py`, `configuration.py` | Main application logic |
| **Data Models** | `models.py` | Database ORM models |
| **Clients** | `openai_client.py` | External service clients |
| **Business Logic** | `room.py`, `storage.py`, `task.py` | Domain-specific logic |
| **Utilities** | `utils/*.py` | Reusable helper functions |
| **Commands** | `commands/*.py` | Bot command handlers |
| **Listeners** | `listeners/*.py` | Event listeners |
| **Global State** | `globals.py` | Application-wide state |
| **Deprecated** | `*_utils.py`, `*_functions.py` | Backward compatibility |

## Migration Checklist

- [x] Create `utils/` package directory
- [x] Move/copy utilities to appropriate modules
- [x] Create `utils/__init__.py` with exports
- [x] Create backward compatibility wrappers
- [x] Add deprecation warnings
- [x] Document new structure
- [ ] Update command files to use new decorators
- [ ] Update existing imports (can be done gradually)
- [ ] Add unit tests for utils
- [ ] Update CI/CD if needed
- [ ] Remove old wrapper files (future)
