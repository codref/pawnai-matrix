#!/usr/bin/env python3
"""
Script to populate the database with default configuration values.

This script will:
1. Connect to the database using the connection string from alembic.ini
2. Create the bot_configuration table if it doesn't exist
3. Populate it with default configuration values

Usage:
    python scripts/populate_config_defaults.py [config_name]
    
    # Populate with "default" as config_name
    python scripts/populate_config_defaults.py
    
    # Populate with custom config_name
    python scripts/populate_config_defaults.py production
"""

import sys
import os

# Add parent directory to path to import pawnai_bob modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pawnai_bob.models import Base
from pawnai_bob.utils import populate_defaults, get_config_dict
from pawnai_bob.configuration import Configuration
from pawnai_bob.settings import resolve_config_path


def get_database_url():
    """Read database URL from config.yaml"""
    try:
        config = Configuration(str(resolve_config_path()))
        return config.database_connection_string
    except Exception as e:
        print(f"Warning: Could not read config.yaml: {e}")
        print("Falling back to SQLite database...")
        return "sqlite:///bot_config.db"


def main():
    config_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    
    print(f"Populating configuration with name: {config_name}")
    
    # Get database URL from alembic.ini
    database_url = get_database_url()
    print(f"Using database: {database_url}")
    
    # Create engine and tables
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    # Populate defaults
    with Session(engine) as session:
        print(f"Populating default configuration values...")
        populate_defaults(session, config_name)
        session.commit()
        
        # Verify
        config = get_config_dict(session, config_name)
        print(f"\nSuccessfully populated {len(config)} configuration entries:")
        
        # Print some sample values
        sample_keys = [
            "openai.url",
            "matrix.user_id",
            "matrix.command_prefix",
            "storage.store_path",
            "storage.temp_path",
        ]
        
        for key in sample_keys:
            if key in config:
                print(f"  {key}: {config[key]}")
        
        print(f"\nTotal configuration entries: {len(config)}")
        print(f"Configuration name: {config_name}")


if __name__ == "__main__":
    main()
