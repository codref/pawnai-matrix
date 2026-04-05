"""
Matrix Bob utilities package.

This package contains various utility modules organized by functionality:
- config: Configuration management utilities
- chat: Chat and messaging helper functions
- decorators: Function decorators for commands
- document: Document data model
- errors: Custom exception classes
"""

from pawnai_bob.utils.config import (
    get_default_configuration,
    populate_defaults,
    populate_config_from_yaml,
    get_config_dict,
    get_value,
    set_value,
    delete_config,
    list_config_names,
)

from pawnai_bob.utils.chat import (
    send_text_to_room,
    make_pill,
    react_to_event,
    get_related_reply_to_events,
    get_reply_body,
    download_event_resources,
)

from pawnai_bob.utils.decorators import (
    matrix_command,
    power_user_function,
)

from pawnai_bob.utils.document import Document

from pawnai_bob.utils.errors import ConfigError

__all__ = [
    # Config utilities
    "get_default_configuration",
    "populate_defaults",
    "populate_config_from_yaml",
    "get_config_dict",
    "get_value",
    "set_value",
    "delete_config",
    "list_config_names",
    # Chat utilities
    "send_text_to_room",
    "make_pill",
    "react_to_event",
    "get_related_reply_to_events",
    "get_reply_body",
    "download_event_resources",
    # Decorators
    "matrix_command",
    "power_user_function",
    # Document model
    "Document",
    # Errors
    "ConfigError",
]
