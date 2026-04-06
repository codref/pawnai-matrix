import logging
import json

from nio import (MatrixRoom)
from sqlalchemy import select
from pawnai_bob.models import Expert, RoomConfiguration
from pawnai_bob.openai_client import OpenAIClient

log = logging.getLogger(__name__)


class Room:
    """Creates an room configuration object storing the LLM"""

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
                return self._create_default_configuration()
            
            conf = json.loads(room_config.configuration)
            expert = self._fetch_expert_if_exists(session, room_config.expert_id)
            
            return self._build_configuration(
                expert_id=room_config.expert_id,
                expert_name=expert.name if expert else "",
                json_config=conf
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

    def _build_configuration(self, expert_id: int | None, expert_name: str, json_config: dict) -> dict:
        """Build configuration dictionary from components"""
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
        }

    def _create_default_configuration(self) -> dict:
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
    
    def get_client(self, matrix_room: MatrixRoom):
        """Get client for the room, lazily initializing it on first access."""
        conf = self.get(matrix_room)
        if conf['client'] is None:
            conf['client'] = OpenAIClient(self.settings, matrix_room.room_id)
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
            configuration = json.dumps({
                    "echo": current_rc["echo"],
                    "free_speak": current_rc["free_speak"],
                    "speak": current_rc["speak"],
                    "tts_voice": current_rc["tts_voice"],
                    "tts_language": current_rc["tts_language"],
                    "tts_model": current_rc["tts_model"],
                    "users": current_rc["users"],
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
