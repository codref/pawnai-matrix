from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String, Text, JSON, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Expert(Base):
    __tablename__ = "expert"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    description: Mapped[Optional[str]]
    configuration: Mapped[str] = mapped_column(String())

    def __repr__(self) -> str:
        return f"Expert(id={self.id!r}, name={self.name!r}, description={self.description!r})"
    

class RoomConfiguration(Base):
    __tablename__ = "room"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[str] = mapped_column(String())
    expert_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("expert.id"), nullable=True
    )
    configuration: Mapped[str] = mapped_column(String())

    def __repr__(self) -> str:
        return f"Expert(id={self.id!r}, room_id={self.room_id!r}, expert_id={self.expert_id!r})"    


class BotConfiguration(Base):
    """
    SQLAlchemy model for bot configuration stored as key-value pairs in PostgreSQL.
    
    This model stores configuration settings as individual key-value pairs, allowing
    flexible configuration management without schema changes.
    
    Usage:
        # Get a configuration value
        config = session.query(BotConfiguration).filter_by(
            config_name="default", 
            key="openai.url"
        ).first()
        print(config.value)
        
        # Using the helper method
        value = BotConfiguration.get_value(session, "openai.url", "default")
    """
    __tablename__ = "bot_configuration"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    config_name: Mapped[str] = mapped_column(String(100), index=True)
    key: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(Text)
    
    def __repr__(self) -> str:
        return f"BotConfiguration(config_name={self.config_name!r}, key={self.key!r}, value={self.value!r})"
    
    @staticmethod
    def get_value(session, key: str, config_name: str = "default", default=None):
        """
        Get a configuration value by key.
        
        Args:
            session: SQLAlchemy session
            key: Configuration key
            config_name: Name of the configuration set (default: "default")
            default: Default value if key not found
            
        Returns:
            The configuration value, or default if not found
        """
        import json
        
        result = session.query(BotConfiguration).filter_by(
            config_name=config_name,
            key=key
        ).first()
        
        if not result:
            return default
        
        # Try to parse JSON values (for lists, dicts, etc.)
        try:
            return json.loads(result.value)
        except (json.JSONDecodeError, TypeError):
            # Return as string if not JSON
            return result.value
    
    @staticmethod
    def set_value(session, key: str, value, config_name: str = "default"):
        """
        Set a configuration value.
        
        Args:
            session: SQLAlchemy session
            key: Configuration key
            value: Configuration value (will be JSON-encoded if not a string)
            config_name: Name of the configuration set (default: "default")
            
        Returns:
            The BotConfiguration object
        """
        import json
        
        # Convert value to string (JSON if not already a string)
        if isinstance(value, str):
            str_value = value
        else:
            str_value = json.dumps(value)
        
        # Check if key exists
        config = session.query(BotConfiguration).filter_by(
            config_name=config_name,
            key=key
        ).first()
        
        if config:
            config.value = str_value
        else:
            config = BotConfiguration(
                config_name=config_name,
                key=key,
                value=str_value
            )
            session.add(config)
        
        return config


class RoomMessage(Base):
    """
    SQLAlchemy model for storing messages from Matrix rooms.
    
    This model stores text messages sent to rooms with metadata including
    the room ID, author (sender), content, timestamp, and additional metadata.
    
    Usage:
        # Create and store a new message
        message = RoomMessage(
            room_id="!abc123:matrix.org",
            author="@user:matrix.org",
            text="Hello, this is a message",
            timestamp=datetime.utcnow()
        )
        session.add(message)
        session.commit()
        
        # Query messages from a room
        messages = session.query(RoomMessage).filter_by(
            room_id="!abc123:matrix.org"
        ).all()
    """
    __tablename__ = "room_message"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(255), index=True)
    text: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    message_metadata: Mapped[Optional[str]] = mapped_column(JSON)
    
    def __repr__(self) -> str:
        return f"RoomMessage(id={self.id!r}, room_id={self.room_id!r}, author={self.author!r}, timestamp={self.timestamp!r})"
