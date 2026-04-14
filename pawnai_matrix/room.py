import logging
import json

from nio import (MatrixRoom)
from sqlalchemy import select
from pawnai_matrix.models import Expert, RoomConfiguration
from pawnai_matrix.openai_client import OpenAIClient
from pawnai_matrix.utils import get_thread_root_event_id

log = logging.getLogger(__name__)


class Room:
    """Creates an room configuration object storing the LLM"""
    DEFAULT_SESSION_ALIAS = "default"

    def __init__(self, settings, store):
        self.settings = settings
        self.store = store
        self.configuration = {}

    def get(self, matrix_room: MatrixRoom):
        '''Return a room configuration'''
        if matrix_room.room_id in self.configuration:
            return self.configuration[matrix_room.room_id]
        
        self.configuration[matrix_room.room_id] = self._load_room_configuration(matrix_room)
        return self.configuration[matrix_room.room_id]

    def _load_room_configuration(self, matrix_room: MatrixRoom) -> dict:
        """Load room configuration from database or create default"""
        with self.store.get_session() as session:
            room_config = self._fetch_room_config_from_db(session, matrix_room.room_id)
            
            if room_config is None:
                return self._create_default_configuration(matrix_room.room_id)
            
            conf = json.loads(room_config.configuration)
            expert = self._fetch_expert_if_exists(session, room_config.expert_id)
            
            return self._build_configuration(
                expert_id=room_config.expert_id,
                expert_name=expert.name if expert else "",
                json_config=conf,
                room_id=matrix_room.room_id,
            )

    def _fetch_room_config_from_db(self, session, room_id) -> RoomConfiguration | None:
        """Fetch room configuration from database"""
        stmt = select(RoomConfiguration).filter(
            RoomConfiguration.room_id == room_id
        )
        return session.scalar(stmt)

    def _fetch_expert_if_exists(self, session, expert_id) -> Expert | None:
        """Fetch expert by ID, raises if expert_id is valid but expert not found"""
        if expert_id in (-1, None):
            return None
        
        stmt = select(Expert).filter(Expert.id == expert_id)
        expert = session.scalar(stmt)
        
        if expert is None:
            raise Exception(
                f"Expert {expert_id} not found. Check room configuration."
            )
        return expert

    def _build_configuration(self, expert_id: int | None, expert_name: str, json_config: dict,
                             room_id: str | None = None) -> dict:
        """Build configuration dictionary from components"""
        normalized_sessions, current_session = self._normalize_sessions(
            json_config,
            room_id or "",
        )

        return {
            'client': None,
            'expert_id': expert_id if expert_id is not None else -1,
            'expert_name': expert_name,
            'echo': json_config.get("echo", True),
            'free_speak': json_config.get("free_speak", False),
            'speak': json_config.get("speak", False),
            'tts_voice': json_config.get("tts_voice", None),
            'tts_language': json_config.get("tts_language", None),
            'tts_model': json_config.get("tts_model", None),
            'users': json_config.get("users", {}),
            'sessions': normalized_sessions,
            'current_session': current_session,
        }

    def _normalize_sessions(self, json_config: dict, room_id: str) -> tuple[dict[str, str], str]:
        """Normalize persisted session mapping and active alias."""
        raw_sessions = json_config.get("sessions")
        sessions: dict[str, str] = {}

        if isinstance(raw_sessions, dict):
            for alias, session_id in raw_sessions.items():
                if isinstance(alias, str) and alias and isinstance(session_id, str) and session_id:
                    sessions[alias] = session_id

        # Keep backward compatibility: when room_id is available, `default` maps to room_id.
        if room_id:
            sessions[self.DEFAULT_SESSION_ALIAS] = room_id
        elif self.DEFAULT_SESSION_ALIAS not in sessions:
            sessions[self.DEFAULT_SESSION_ALIAS] = ""

        if not sessions:
            sessions = {
                self.DEFAULT_SESSION_ALIAS: room_id
            }

        current_session = json_config.get("current_session")
        if not isinstance(current_session, str) or current_session not in sessions:
            current_session = self.DEFAULT_SESSION_ALIAS

        return sessions, current_session

    def _create_default_configuration(self, room_id: str = "") -> dict:
        """Create a default configuration"""
        return {
            'client': None,
            'expert_id': -1,
            'expert_name': "",
            'echo': True,
            'free_speak': False,
            'speak': False,
            'tts_voice': None,
            'tts_language': None,
            'tts_model': None,
            'users': {},
            'sessions': {
                self.DEFAULT_SESSION_ALIAS: room_id,
            },
            'current_session': self.DEFAULT_SESSION_ALIAS,
        }
    
    # Property Getters
    def get_echo(self, matrix_room: MatrixRoom) -> bool:
        """Get echo setting for the room"""
        return self.get(matrix_room)['echo']
    
    def get_users(self, matrix_room: MatrixRoom) -> dict:
        """Get users mapping configuration for the room"""
        return self.get(matrix_room)['users']

    def get_free_speak(self, matrix_room: MatrixRoom) -> bool:
        """Get free speak setting for the room"""
        return self.get(matrix_room)['free_speak']

    def get_speak(self, matrix_room: MatrixRoom) -> bool:
        """Get speak (TTS output) setting for the room"""
        return self.get(matrix_room)['speak']

    def get_tts_voice(self, matrix_room: MatrixRoom):
        """Get per-room TTS voice override, or None to use global config"""
        return self.get(matrix_room)['tts_voice']

    def get_tts_language(self, matrix_room: MatrixRoom):
        """Get per-room TTS language override, or None to use global config"""
        return self.get(matrix_room)['tts_language']

    def get_tts_model(self, matrix_room: MatrixRoom):
        """Get per-room TTS model override, or None to use global config"""
        return self.get(matrix_room)['tts_model']
    
    def get_expert_id(self, matrix_room: MatrixRoom) -> int:
        """Get expert ID for the room"""
        return self.get(matrix_room)['expert_id']
    
    def get_expert_name(self, matrix_room: MatrixRoom) -> str:
        """Get expert name for the room"""
        return self.get(matrix_room)['expert_name']

    def get_sessions(self, matrix_room: MatrixRoom) -> dict[str, str]:
        """Get the session alias mapping for the room."""
        return self.get(matrix_room)['sessions']

    def get_current_session_alias(self, matrix_room: MatrixRoom) -> str:
        """Get the active session alias for the room."""
        return self.get(matrix_room)['current_session']

    def get_current_session_id(self, matrix_room: MatrixRoom) -> str:
        """Get the active session id for the room."""
        conf = self.get(matrix_room)
        alias = conf['current_session']
        return conf['sessions'][alias]

    def get_session_id(self, matrix_room: MatrixRoom, alias: str) -> str | None:
        """Get the session id for a given alias, if present."""
        return self.get_sessions(matrix_room).get(alias)

    def build_thread_session_id(self, matrix_room: MatrixRoom,
                                thread_root_event_id: str) -> str:
        """Build a deterministic thread-scoped session identifier."""
        return f"{matrix_room.room_id}::thread::{thread_root_event_id}"

    def resolve_session_id(self, matrix_room: MatrixRoom, event=None) -> str:
        """Resolve the room session id, preferring thread-scoped sessions."""
        thread_root_event_id = get_thread_root_event_id(event)
        if thread_root_event_id:
            return self.build_thread_session_id(matrix_room, thread_root_event_id)
        return self.get_current_session_id(matrix_room)
    
    def get_client(self, matrix_room: MatrixRoom, event=None):
        """Get client for the room, lazily initializing it on first access."""
        conf = self.get(matrix_room)
        if conf['client'] is None:
            conf['client'] = OpenAIClient(self.settings, matrix_room.room_id)
        conf['client'].set_session_id(self.resolve_session_id(matrix_room, event))
        return conf['client']
    
    def _set_and_save(self, matrix_room: MatrixRoom, key: str, value):
        """Update a single config key, persist to DB, and invalidate cache."""
        self.get(matrix_room)[key] = value
        self.save_configuration(matrix_room)
        del self.configuration[matrix_room.room_id]

    def set_echo(self, matrix_room: MatrixRoom, echo):
        self._set_and_save(matrix_room, "echo", echo)

    def set_users(self, matrix_room: MatrixRoom, users):
        self._set_and_save(matrix_room, "users", users)

    def set_free_speak(self, matrix_room: MatrixRoom, free_speak):
        self._set_and_save(matrix_room, "free_speak", free_speak)

    def set_speak(self, matrix_room: MatrixRoom, speak: bool):
        self._set_and_save(matrix_room, "speak", speak)

    def set_tts_voice(self, matrix_room: MatrixRoom, voice):
        self._set_and_save(matrix_room, "tts_voice", voice)

    def set_tts_language(self, matrix_room: MatrixRoom, language):
        self._set_and_save(matrix_room, "tts_language", language)

    def set_tts_model(self, matrix_room: MatrixRoom, model):
        self._set_and_save(matrix_room, "tts_model", model)

    def _persist_and_invalidate(self, matrix_room: MatrixRoom):
        self.save_configuration(matrix_room)
        del self.configuration[matrix_room.room_id]

    def build_session_id(self, matrix_room: MatrixRoom, alias: str) -> str:
        """Build a deterministic room-scoped session identifier."""
        return f"{matrix_room.room_id}::session::{alias}"

    def create_session(self, matrix_room: MatrixRoom, alias: str) -> str:
        """Create a room session alias and switch to it."""
        conf = self.get(matrix_room)
        if alias in conf['sessions']:
            raise ValueError(f"Session `{alias}` already exists.")

        session_id = self.build_session_id(matrix_room, alias)
        conf['sessions'][alias] = session_id
        conf['current_session'] = alias
        self._persist_and_invalidate(matrix_room)
        return session_id

    def use_session(self, matrix_room: MatrixRoom, alias: str) -> str:
        """Switch active room session to an existing alias."""
        conf = self.get(matrix_room)
        if alias not in conf['sessions']:
            raise ValueError(f"Session `{alias}` not found.")

        conf['current_session'] = alias
        self._persist_and_invalidate(matrix_room)
        return conf['sessions'][alias]

    def set_expert(self, matrix_room: MatrixRoom, expert_id):
        """
        Set a new room configuration
        """
        current_rc = self.get(matrix_room)
        current_rc["expert_id"] = expert_id

        self.save_configuration(matrix_room)

        # invalidate room entry to force reload at next use
        del self.configuration[matrix_room.room_id]  


    def save_configuration(self, matrix_room: MatrixRoom):
        """
        Save or update configuration to DB
        """
        current_rc = self.get(matrix_room)
        with self.store.get_session() as session:
            # check if configuration already exists for this room
            stmt = select(RoomConfiguration).filter(
                RoomConfiguration.room_id == matrix_room.room_id)
            rc = session.scalar(stmt)
            sessions, current_session = self._normalize_sessions(
                {
                    "sessions": current_rc.get("sessions"),
                    "current_session": current_rc.get("current_session"),
                },
                matrix_room.room_id,
            )
            configuration = json.dumps({
                    "echo": current_rc["echo"],
                    "free_speak": current_rc["free_speak"],
                    "speak": current_rc["speak"],
                    "tts_voice": current_rc["tts_voice"],
                    "tts_language": current_rc["tts_language"],
                    "tts_model": current_rc["tts_model"],
                    "users": current_rc["users"],
                    "sessions": sessions,
                    "current_session": current_session,
                })
            expert_id = current_rc["expert_id"]
            persisted_expert_id = None if expert_id in (-1, None) else expert_id
            if rc is not None:
                rc.expert_id = persisted_expert_id
                rc.configuration = configuration
            else:
                new_rc = RoomConfiguration(
                    room_id=matrix_room.room_id,
                    expert_id=persisted_expert_id,
                    configuration=configuration
                    )
                session.add(new_rc)
            session.commit()
