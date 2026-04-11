import logging
import os

from pawnai_matrix.utils.errors import ConfigError
from pawnai_matrix.settings import BobSettings

log = logging.getLogger(__name__)


class Configuration:
    """Creates a Config object from a YAML-encoded config file to retrieve the PostgreSQL database URI"""

    def __init__(self, config_file_path: str):
        # Read user-configured options from a config file.
        self.filepath = config_file_path

        if not os.path.isfile(self.filepath):
            raise ConfigError(f"Config file '{self.filepath}' does not exist")

        try:
            self.settings = BobSettings.from_yaml(self.filepath)
        except Exception as exc:
            raise ConfigError(str(exc)) from exc

        self.config_dict = self.settings.to_dict()
        self.database_connection_string = self.settings.database_connection_string
        self.configuration_name = self.settings.configuration_name
