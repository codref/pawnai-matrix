import logging
import os
from typing import Any, List, Optional

import yaml

from pawnai_bob.utils import ConfigError

log = logging.getLogger(__name__)


class Configuration:
    """Creates a Config object from a YAML-encoded config file to retrieve the PostgreSQL database URI"""

    def __init__(self, config_file_path):
        # Read user-configured options from a config file.
        self.filepath = config_file_path

        if not os.path.isfile(self.filepath):
            raise ConfigError(f"Config file '{self.filepath}' does not exist")

        # Load in the config file at the given filepath
        with open(self.filepath) as file_stream:
            self.config_dict = yaml.safe_load(file_stream.read())

        # Parse and validate config options
        self._parse_config_values()

    def _parse_config_values(self):
        """Read and validate the database URI and configuration name"""
        # Database setup - retrieve only the PostgreSQL database URI
        self.database_connection_string = self._get_cfg(["storage", "database"], required=True)
        
        # Configuration name
        self.configuration_name = self._get_cfg(["configuration", "name"], default="default")        

    def _get_cfg(
        self,
        path: List[str],
        default: Optional[Any] = None,
        required: Optional[bool] = True,
    ) -> Any:
        """Get a config option from a path and option name, specifying whether it is
        required.

        Raises:
            ConfigError: If required is True and the object is not found (and there is
                no default value provided), a ConfigError will be raised.
        """
        # Sift through the the config until we reach our option
        config = self.config_dict
        for name in path:
            config = config.get(name)

            # If at any point we don't get our expected option...
            if config is None:
                # Raise an error if it was required
                if required and not default:
                    raise ConfigError(
                        f"Config option {'.'.join(path)} is required")

                # or return the default value
                return default

        # We found the option. Return it.
        return config
