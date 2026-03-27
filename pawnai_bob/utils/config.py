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
        print(f"OpenAI URL: {config_dict['openai_url']}")
"""

import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from pawnai_bob.models import BotConfiguration


def get_default_configuration() -> Dict[str, Any]:
    """
    Get default configuration values based on the Configuration class defaults.
    
    Returns:
        Dictionary of default configuration values
    """
    return {
        # Storage
        "storage.store_path": "./store",
        "storage.temp_path": "./tmp",
        "storage.database": "sqlite:///bot.db",
        
        # Qdrant
        "qdrant.url": "http://localhost:6333",
        "qdrant.default_collection_name": "default",
        
        # Whisper
        "whisper.default_model": "small",
        "whisper.models": ["small.en", "small", "medium.en", "medium", "large"],
        
        # Huggingface
        "huggingface.api_key": None,
        "huggingface.inference_api_models_url": "https://api-inference.huggingface.co/models",
        
        # Groq
        "groq.api_key": None,
        
        # Nvidia
        "nvidia.api_key": None,
        "nvidia.inference_api_models_url": "https://ai.api.nvidia.com/v1/genai",
        
        # Vision
        "vision.client": "groq",
        "vision.default_itt_model": "ollama/qwen2.5vl:7b",
        "vision.models": ["ollama/qwen2.5vl:7b"],
        "vision.model_temperature": 0.5,
        "vision.max_tokens": 700,
        "vision.default_query": "You are a verbose chatbot. Describe the attached image in detail.",
        
        # Image Generation
        "image_generation.client": "nvidia",
        "image_generation.default_tti_model": "stabilityai/stable-diffusion-3-medium",
        "image_generation.models": ["stabilityai/stable-diffusion-3-medium"],
        
        # OpenAI
        "openai.url": "http://localhost:11434/v1",
        "openai.api_key": "ollama",
        "openai.default_model": "mistral",
        "openai.default_llm_model": "ollama/mistral-nemo",
        "openai.llm_models": [
            "ollama/mistral-small:24b",
            "ollama/mixtral:8x7b",
            "ollama/deepseek-r1:8b",
            "ollama/gemma3:4b",
            "ollama/mistral-nemo"
        ],
        "openai.default_embed_model": "qwen3-embedding-s",
        "openai.embed_models": ["qwen3-embedding-s"],
        "openai.default_prompt": "You are Bob the chatbot and you are able to have normal interactions",
        "openai.default_context_length": 1500,
        "openai.timeout": 60000,
        "openai.default_chunk_size": 1024,
        
        # Tasks
        "tasks.path": "./tasks",
        
        # Matrix
        "matrix.user_id": "@bot:matrix.org",
        "matrix.user_password": None,
        "matrix.user_token": None,
        "matrix.device_id": "DEVICE_ID",
        "matrix.device_name": "nio-template",
        "matrix.homeserver_url": "https://matrix.org",
        "matrix.command_prefix": "!c ",
        
        # User lists
        "matrix.inviters": [],
        "matrix.power_users": [],
    }


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
    import yaml
    import os
    
    if not os.path.isfile(yaml_file_path):
        raise ValueError(f"Config file '{yaml_file_path}' does not exist")
    
    # Load YAML file
    with open(yaml_file_path) as file_stream:
        yaml_config = yaml.safe_load(file_stream.read())
    
    # Helper function to get nested values from YAML
    def get_yaml_value(path: list, default=None):
        value = yaml_config
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value
    
    # Get defaults for comparison
    defaults = get_default_configuration()
    
    # Map YAML paths to database keys
    config_dict = {
        # Storage
        "storage.store_path": get_yaml_value(["storage", "store_path"], defaults["storage.store_path"]),
        "storage.temp_path": get_yaml_value(["storage", "temp_path"], defaults["storage.temp_path"]),
        "storage.database": get_yaml_value(["storage", "database"], defaults["storage.database"]),
        
        # Qdrant
        "qdrant.url": get_yaml_value(["qdrant", "url"], defaults["qdrant.url"]),
        "qdrant.default_collection_name": get_yaml_value(["qdrant", "default_collection_name"], defaults["qdrant.default_collection_name"]),
        
        # Whisper
        "whisper.default_model": get_yaml_value(["whisper", "default_model"], defaults["whisper.default_model"]),
        "whisper.models": get_yaml_value(["whisper", "models"], defaults["whisper.models"]),
        
        # Huggingface
        "huggingface.api_key": get_yaml_value(["huggingface", "api_key"], defaults["huggingface.api_key"]),
        "huggingface.inference_api_models_url": get_yaml_value(["huggingface", "inference_api_models_url"], defaults["huggingface.inference_api_models_url"]),
        
        # Groq
        "groq.api_key": get_yaml_value(["groq", "api_key"], defaults["groq.api_key"]),
        
        # Nvidia
        "nvidia.api_key": get_yaml_value(["nvidia", "api_key"], defaults["nvidia.api_key"]),
        "nvidia.inference_api_models_url": get_yaml_value(["nvidia", "inference_api_models_url"], defaults["nvidia.inference_api_models_url"]),
        
        # Vision
        "vision.client": get_yaml_value(["vision", "client"], defaults["vision.client"]),
        "vision.default_itt_model": get_yaml_value(["vision", "default_itt_model"], defaults["vision.default_itt_model"]),
        "vision.models": get_yaml_value(["vision", "models"], defaults["vision.models"]),
        "vision.model_temperature": get_yaml_value(["vision", "model_temperature"], defaults["vision.model_temperature"]),
        "vision.max_tokens": get_yaml_value(["vision", "max_tokens"], defaults["vision.max_tokens"]),
        "vision.default_query": get_yaml_value(["vision", "default_query"], defaults["vision.default_query"]),
        
        # Image Generation
        "image_generation.client": get_yaml_value(["image_generation", "client"], defaults["image_generation.client"]),
        "image_generation.default_tti_model": get_yaml_value(["image_generation", "default_tti_model"], defaults["image_generation.default_tti_model"]),
        "image_generation.models": get_yaml_value(["image_generation", "models"], defaults["image_generation.models"]),
        
        # OpenAI
        "openai.url": get_yaml_value(["openai", "url"], defaults["openai.url"]),
        "openai.api_key": get_yaml_value(["openai", "api_key"], defaults["openai.api_key"]),
        "openai.default_model": get_yaml_value(["openai", "default_model"], defaults["openai.default_model"]),
        "openai.default_llm_model": get_yaml_value(["openai", "default_llm_model"], defaults["openai.default_llm_model"]),
        "openai.llm_models": get_yaml_value(["openai", "llm_models"], defaults["openai.llm_models"]),
        "openai.default_embed_model": get_yaml_value(["openai", "default_embed_model"], defaults["openai.default_embed_model"]),
        "openai.embed_models": get_yaml_value(["openai", "embed_models"], defaults["openai.embed_models"]),
        "openai.default_prompt": get_yaml_value(["openai", "default_prompt"], defaults["openai.default_prompt"]),
        "openai.default_context_length": get_yaml_value(["openai", "default_context_length"], defaults["openai.default_context_length"]),
        "openai.timeout": get_yaml_value(["openai", "timeout"], defaults["openai.timeout"]),
        "openai.default_chunk_size": get_yaml_value(["openai", "default_chunk_size"], defaults["openai.default_chunk_size"]),
        
        # Tasks
        "tasks.path": get_yaml_value(["tasks", "path"], defaults["tasks.path"]),
        
        # Matrix
        "matrix.user_id": get_yaml_value(["matrix", "user_id"], defaults["matrix.user_id"]),
        "matrix.user_password": get_yaml_value(["matrix", "user_password"], defaults["matrix.user_password"]),
        "matrix.user_token": get_yaml_value(["matrix", "user_token"], defaults["matrix.user_token"]),
        "matrix.device_id": get_yaml_value(["matrix", "device_id"], defaults["matrix.device_id"]),
        "matrix.device_name": get_yaml_value(["matrix", "device_name"], defaults["matrix.device_name"]),
        "matrix.homeserver_url": get_yaml_value(["matrix", "homeserver_url"], defaults["matrix.homeserver_url"]),
        "matrix.command_prefix": get_yaml_value(["matrix", "command_prefix"], defaults["matrix.command_prefix"]),
        
        # User lists
        "matrix.inviters": get_yaml_value(["matrix", "inviters"], defaults["matrix.inviters"]),
        "matrix.power_users": get_yaml_value(["matrix", "power_users"], defaults["matrix.power_users"]),
    }
    
    for key, value in config_dict.items():
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
            print(f"OpenAI URL: {config['openai_url']}")
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
            url = get_value(session, "openai_url", "production")
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
            set_value(session, "openai_url", "http://localhost:11434/v1")
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

