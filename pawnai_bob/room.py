import logging
import json

from nio import (MatrixRoom)
from sqlalchemy import select, update
from pawnai_bob.models import Expert, RoomConfiguration

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
        if expert_id == -1:
            return None
        
        stmt = select(Expert).filter(Expert.id == expert_id)
        expert = session.scalar(stmt)
        
        if expert is None:
            raise Exception(
                f"Expert {expert_id} not found. Check room configuration."
            )
        return expert

    def _build_configuration(self, expert_id: int, expert_name: str, json_config: dict) -> dict:
        """Build configuration dictionary from components"""
        return {
            'client': None,
            'vision_client': None,
            'expert_id': expert_id,
            'expert_name': expert_name,
            'echo': json_config.get("echo", True),
            'users': json_config.get("users", {}),
            'index-conversation': json_config.get("index-conversation", False),
            'vision-two-steps': json_config.get("vision-two-steps", False),
        }

    def _create_default_configuration(self) -> dict:
        """Create a default configuration"""
        return {
            'client': None,
            'vision_client': None,
            'expert_id': -1,
            'expert_name': "",
            'echo': True,
            'users': {},
            'index-conversation': False,
            'vision-two-steps': False,
        }
    
    # Property Getters
    def get_echo(self, matrix_room: MatrixRoom) -> bool:
        """Get echo setting for the room"""
        return self.get(matrix_room)['echo']
    
    def get_vision_two_steps(self, matrix_room: MatrixRoom) -> bool:
        """Get vision-two-steps setting for the room"""
        return self.get(matrix_room)['vision-two-steps']
    
    def get_index_conversation(self, matrix_room: MatrixRoom) -> bool:
        """Get index-conversation setting for the room"""
        return self.get(matrix_room)['index-conversation']
    
    def get_users(self, matrix_room: MatrixRoom) -> dict:
        """Get users mapping configuration for the room"""
        return self.get(matrix_room)['users']
    
    def get_expert_id(self, matrix_room: MatrixRoom) -> int:
        """Get expert ID for the room"""
        return self.get(matrix_room)['expert_id']
    
    def get_expert_name(self, matrix_room: MatrixRoom) -> str:
        """Get expert name for the room"""
        return self.get(matrix_room)['expert_name']
    
    def get_client(self, matrix_room: MatrixRoom):
        """Get client for the room"""
        return self.get(matrix_room)['client']
    
    def get_vision_client(self, matrix_room: MatrixRoom):
        """Get vision client for the room"""
        return self.get(matrix_room)['vision_client']
    
    def set_echo(self, matrix_room: MatrixRoom, echo):
        """
        Set echo for the given room
        """
        current_rc = self.get(matrix_room)
        current_rc["echo"] = echo

        self.save_configuration(matrix_room)

    def set_vision_two_steps(self, matrix_room: MatrixRoom, vision_two_steps):
        """
        Set echo for the given room
        """
        current_rc = self.get(matrix_room)
        current_rc["vision-two-steps"] = vision_two_steps

        self.save_configuration(matrix_room)        

    def set_index_conversation(self, matrix_room: MatrixRoom, index_conversation):
        """
        Set echo for the given room
        """
        current_rc = self.get(matrix_room)
        current_rc["index-conversation"] = index_conversation

        self.save_configuration(matrix_room)        

    def set_users(self, matrix_room: MatrixRoom, users):
        """
        Set the users mapping configuration
        """
        current_rc = self.get(matrix_room)
        current_rc["users"] = users
        
        self.save_configuration(matrix_room)

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
                    "users": current_rc["users"]
                })
            if rc is not None:
                rc.expert_id = current_rc["expert_id"]
                rc.configuration = configuration
            else:
                new_rc = RoomConfiguration(
                    room_id=matrix_room.room_id,
                    expert_id=current_rc["expert_id"],
                    configuration=configuration
                    )
                session.add(new_rc)
            session.commit()

        
                   

