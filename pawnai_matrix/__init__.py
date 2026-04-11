'''
    Matrix Bob module
'''
from pawnai_matrix.globals import (
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
    set_debug_tts_transcript,
    get_debug_tts_transcript,
    has_debug_tts_transcript,
    is_initialized,
    init,
    reset,
    NotInitializedError,
)

# Backward compatibility alias
g = get_debug_dict

