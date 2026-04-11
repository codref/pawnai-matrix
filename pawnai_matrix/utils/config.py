"""
Utility module for working with BotConfiguration ORM model (key-value storage).

This module provides helper functions to convert between the Configuration
class (which reads from YAML files) and the BotConfiguration ORM model
(which stores configuration as key-value pairs in PostgreSQL).

Usage example:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from pawnai_bob.models import Base, BotConfiguration
    from pawnai_bob.utils import populate_config_from_yaml, get_config_dict
    
    # Create database tables
    engine = create_engine("postgresql://user:password@localhost/dbname")
    Base.metadata.create_all(engine)
    
    # Populate database from YAML configuration file
    with Session(engine) as session:
        populate_config_from_yaml(session, "config.yaml", config_name="production")
        session.commit()
    
    # Load configuration from database as dictionary
    with Session(engine) as session:
        config_dict = get_config_dict(session, "production")
        print(f"OpenAI URL: {config_dict['openai.url']}")
"""

import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from pawnai_bob.models import BotConfiguration
from pawnai_bob.settings import BobSettings


def get_default_configuration() -> Dict[str, Any]:
    """
    Get default configuration values based on the Configuration class defaults.
    
    Returns:
        Dictionary of default configuration values
    """
    return BobSettings().to_runtime_flat_dict()


def populate_defaults(session: Session, config_name: str = "default") -> None:
    """
    Populate the database with default configuration values.
    
    Args:
        session: SQLAlchemy session
        config_name: Name of the configuration set (default: "default")
    
    Example:
        with Session(engine) as session:
            populate_defaults(session, "default")
            session.commit()
    """
    defaults = get_default_configuration()
    
    for key, value in defaults.items():
        BotConfiguration.set_value(session, key, value, config_name)


def populate_config_from_yaml(
    session: Session,
    yaml_file_path: str,
    config_name: str = "default"
) -> None:
    """
    Populate the database from a YAML configuration file.
    
    Args:
        session: SQLAlchemy session
        yaml_file_path: Path to the YAML configuration file
        config_name: Name of the configuration set (default: "default")
    
    Example:
        with Session(engine) as session:
            populate_config_from_yaml(session, "config.yaml", "production")
            session.commit()
    """
    import os

    if not os.path.isfile(yaml_file_path):
        raise ValueError(f"Config file '{yaml_file_path}' does not exist")

    flattened = BobSettings.from_yaml(yaml_file_path).to_runtime_flat_dict()
    defaults = get_default_configuration()

    for key, default_value in defaults.items():
        value = flattened.get(key, default_value)
        BotConfiguration.set_value(session, key, value, config_name)


def get_config_dict(session: Session, config_name: str = "default") -> Dict[str, Any]:
    """
    Load all configuration from the database as a dictionary.
    
    Args:
        session: SQLAlchemy session
        config_name: Name of the configuration set (default: "default")
    
    Returns:
        Dictionary of all configuration values
    
    Example:
        with Session(engine) as session:
            config = get_config_dict(session, "production")
            print(f"OpenAI URL: {config['openai.url']}")
    """
    configs = session.query(BotConfiguration).filter_by(config_name=config_name).all()
    
    result = {}
    for config in configs:
        # Try to parse JSON values
        try:
            result[config.key] = json.loads(config.value)
        except (json.JSONDecodeError, TypeError):
            result[config.key] = config.value
    
    return result


def get_value(
    session: Session,
    key: str,
    config_name: str = "default",
    default=None
) -> Any:
    """
    Get a single configuration value from the database.
    
    Args:
        session: SQLAlchemy session
        key: Configuration key
        config_name: Name of the configuration set (default: "default")
        default: Default value if key not found
    
    Returns:
        The configuration value, or default if not found
    
    Example:
        with Session(engine) as session:
            url = get_value(session, "openai.url", "production")
    """
    return BotConfiguration.get_value(session, key, config_name, default)


def set_value(
    session: Session,
    key: str,
    value: Any,
    config_name: str = "default"
) -> BotConfiguration:
    """
    Set a single configuration value in the database.
    
    Args:
        session: SQLAlchemy session
        key: Configuration key
        value: Configuration value
        config_name: Name of the configuration set (default: "default")
    
    Returns:
        The BotConfiguration object
    
    Example:
        with Session(engine) as session:
            set_value(session, "openai.url", "http://localhost:11434/v1")
            session.commit()
    """
    return BotConfiguration.set_value(session, key, value, config_name)


def delete_config(session: Session, config_name: str) -> int:
    """
    Delete all configuration entries for a given config_name.
    
    Args:
        session: SQLAlchemy session
        config_name: Name of the configuration set to delete
    
    Returns:
        Number of entries deleted
    
    Example:
        with Session(engine) as session:
            count = delete_config(session, "old_config")
            session.commit()
            print(f"Deleted {count} configuration entries")
    """
    result = session.query(BotConfiguration).filter_by(config_name=config_name).delete()
    return result


def list_config_names(session: Session) -> list[str]:
    """
    List all unique configuration names in the database.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        List of configuration names
    
    Example:
        with Session(engine) as session:
            names = list_config_names(session)
            for name in names:
                print(f"Config: {name}")
    """
    from sqlalchemy import distinct
    
    result = session.query(distinct(BotConfiguration.config_name)).all()
    return [row[0] for row in result]
