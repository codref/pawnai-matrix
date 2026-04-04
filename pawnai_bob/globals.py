"""
    pawnai_bob.globals
    Defines all the global objects with proper type hints and initialization management
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)

from pawnai_bob.configuration import Configuration
from pawnai_bob.database import Storage
from pawnai_bob.room import Room
from pawnai_bob.utils import get_config_dict
from nio import AsyncClient, AsyncClientConfig

# Global state variables with explicit types
_settings: Optional[Configuration] = None
_config_dict: Optional[Dict[str, Any]] = None
_store: Optional[Storage] = None
_client: Optional[AsyncClient] = None
_room_manager: Optional[Room] = None
_started_on: Optional[Any] = None

# Debug/utility dictionary
_debug: Dict[str, Any] = {}

# Track initialization state
_initialized: bool = False


class NotInitializedError(RuntimeError):
    """Raised when accessing globals before initialization"""
    pass



def is_initialized() -> bool:
    """Check if globals have been initialized"""
    return _initialized


def settings() -> Configuration:
    """Get the Configuration object"""
    if _settings is None:
        raise NotInitializedError("Globals not initialized. Call init() first.")
    return _settings


def config() -> Dict[str, Any]:
    """Get the configuration dictionary"""
    if _config_dict is None:
        raise NotInitializedError("Globals not initialized. Call init() first.")
    return _config_dict


def store() -> Storage:
    """Get the Storage/Database object"""
    if _store is None:
        raise NotInitializedError("Globals not initialized. Call init() first.")
    return _store


def client() -> AsyncClient:
    """Get the Matrix AsyncClient object"""
    if _client is None:
        raise NotInitializedError("Globals not initialized. Call init() first.")
    return _client


def room_manager() -> Room:
    """Get the Room configuration manager"""
    if _room_manager is None:
        raise NotInitializedError("Globals not initialized. Call init() first.")
    return _room_manager


def room() -> Room:
    """Alias for room_manager() for backward compatibility"""
    return room_manager()


def get_debug_dict() -> Dict[str, Any]:
    """Get the debug dictionary"""
    return _debug


def set_started_on(timestamp: Any) -> None:
    """Set the application start timestamp"""
    global _started_on
    _started_on = timestamp


def get_started_on() -> Any:
    """Get the application start timestamp"""
    if _started_on is None:
        raise NotInitializedError("Started on timestamp not set. Call set_started_on() first.")
    return _started_on


def _set_debug(key: str, value: Any) -> None:
    _debug[key] = value


def _get_debug(key: str) -> Optional[Any]:
    return _debug.get(key)


def _has_debug(key: str) -> bool:
    return key in _debug


def set_debug_message(message: str) -> None:    _set_debug("message", message)
def get_debug_message() -> Optional[str]:       return _get_debug("message")
def has_debug_message() -> bool:                return _has_debug("message")


def _resolve_runtime_path(settings: Configuration, path_value: Optional[str], fallback: str) -> str:
    """Resolve a runtime path relative to the config file and ensure it exists."""
    raw_path = path_value or fallback
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path(settings.filepath).resolve().parent / path
    path.mkdir(parents=True, exist_ok=True)
    return str(path)



def init(config_file_path: str) -> None:
    """
    Initialize the global variables
    
    Args:
        config_file_path: Path to the configuration file
        
    Raises:
        Exception: If initialization fails
    """
    global _settings, _store, _config_dict, _client, _room_manager, _initialized
    
    try:
        _settings = Configuration(config_file_path)
        _store = Storage(_settings.database_connection_string)    
        
        # Retrieve configuration as dictionary from the database
        _config_dict = get_config_dict(_store.get_session(), _settings.configuration_name)
        _config_dict['storage.store_path'] = _resolve_runtime_path(
            _settings,
            _config_dict.get('storage.store_path'),
            "./store",
        )
        _config_dict['storage.temp_path'] = _resolve_runtime_path(
            _settings,
            _config_dict.get('storage.temp_path'),
            "./tmp",
        )

        # Initialize the matrix client
        _client = AsyncClient(
            _config_dict.get('matrix.homeserver_url'),
            _config_dict.get('matrix.user_id'),
            device_id=_config_dict.get('matrix.device_id'),
            store_path=_config_dict.get('storage.store_path'),
            config=AsyncClientConfig(
                max_limit_exceeded=0,
                max_timeouts=0,
                store_sync_tokens=True,
                encryption_enabled=True,
            ),
        )

        # Initialize room manager
        log.info("======= INITIALIZE Experts =======")
        _room_manager = Room(_config_dict, _store)
        log.info("======= Experts are READY =======")

        _initialized = True
        
    except Exception as e:
        log.error(f"Failed to initialize globals: {e}")
        raise


def reset() -> None:
    """Reset globals (useful for testing or cleanup)"""
    global _settings, _config_dict, _store, _client, _room_manager, _started_on, _initialized
    
    _settings = None
    _config_dict = None
    _store = None
    _client = None
    _room_manager = None
    _started_on = None
    _initialized = False
