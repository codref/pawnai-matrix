#!/usr/bin/env python3
"""
Script to import configuration from YAML file to database.

This script will:
1. Read configuration from a YAML file using the Configuration class
2. Connect to the database
3. Populate the database with values from the YAML file

Usage:
    python scripts/import_yaml_config.py <yaml_file> [config_name]
    
    # Import from config.yaml with "default" as config_name
    python scripts/import_yaml_config.py bin/config.yaml
    
    # Import with custom config_name
    python scripts/import_yaml_config.py bin/config.yaml production
"""

import sys
import os

# Add parent directory to path to import pawnai_bob modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pawnai_bob.models import Base, BotConfiguration
from pawnai_bob.configuration import Configuration
from pawnai_bob.utils import populate_config_from_yaml, get_config_dict


def get_database_url(yaml_file):
    """Read database URL from config.yaml"""
    try:
        config = Configuration(yaml_file)
        return config.database_connection_string
    except Exception as e:
        print(f"Warning: Could not read config.yaml: {e}")
        print("Falling back to SQLite database...")
        return "sqlite:///bot_config.db"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_yaml_config.py <yaml_file> [config_name]")
        print("\nExample:")
        print("  python scripts/import_yaml_config.py bin/config.yaml")
        print("  python scripts/import_yaml_config.py bin/config.yaml production")
        sys.exit(1)
    
    yaml_file = sys.argv[1]
    config_name = sys.argv[2] if len(sys.argv) > 2 else "default"
    
    if not os.path.exists(yaml_file):
        print(f"Error: YAML file not found: {yaml_file}")
        sys.exit(1)
    
    print(f"Importing configuration from: {yaml_file}")
    print(f"Configuration name: {config_name}")
    
    # Get database URL from alembic.ini
    database_url = get_database_url(yaml_file)
    print(f"Using database: {database_url}")
    
    # Create engine and tables
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    # Populate from YAML
    with Session(engine) as session:
        print(f"Importing configuration values to database...")
        populate_config_from_yaml(session, yaml_file, config_name)
        session.commit()
        print(f"✓ Successfully imported configuration from {yaml_file}")
        
        # Verify
        config = get_config_dict(session, config_name)
        print(f"\n✓ Successfully imported {len(config)} configuration entries:")
        
        # Print some important values
        important_keys = [
            "matrix.user_id",
            "matrix.homeserver_url",
            "openai.url",
            "qdrant.url",
            "storage.database",
            "storage.store_path",
            "storage.temp_path"
        ]
        
        for key in important_keys:
            if key in config:
                # Mask sensitive values
                value = config[key]
                if 'password' in key.lower() or 'token' in key.lower() or 'api_key' in key.lower():
                    if value:
                        value = "***HIDDEN***"
                print(f"  {key}: {value}")
        
        print(f"\nTotal configuration entries: {len(config)}")
        print(f"Configuration name: {config_name}")


if __name__ == "__main__":
    main()
