'''
    Matrix Bob module
'''
from pawnai_bob.globals import (
    settings, 
    config,
    store, 
    client, 
    room,
    room_manager,
    get_debug_dict,
    get_started_on,
    set_started_on,
    set_debug_message,
    get_debug_message,
    has_debug_message,
    set_debug_vision,
    get_debug_vision,
    has_debug_vision,
    set_debug_whispered,
    get_debug_whispered,
    has_debug_whispered,
    is_initialized,
    init,
    reset,
    NotInitializedError,
)

# Backward compatibility alias
g = get_debug_dict

