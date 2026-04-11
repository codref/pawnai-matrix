from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _flatten_dict(payload: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for key, value in payload.items():
        dotted_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(_flatten_dict(value, dotted_key))
            continue
        flattened[dotted_key] = value
    return flattened


def resolve_config_path(config_file_path: str | Path | None = None) -> Path:
    if config_file_path:
        return Path(config_file_path).expanduser().resolve()

    env_config_path = os.getenv("BOB_CONFIG_FILE")
    if env_config_path:
        return Path(env_config_path).expanduser().resolve()

    candidates = (
        Path("config.yaml"),
        Path("config/config.yaml"),
        Path("bin/config.yaml"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise FileNotFoundError(
        "Config file not found. Checked: "
        + ", ".join(str(candidate) for candidate in candidates)
    )


class StorageSettings(BaseModel):
    database: str = "sqlite://bob.db"
    store_path: str = "./store"
    temp_path: str = "./tmp"


class OpenAISettings(BaseModel):
    url: str = "http://localhost:4000"
    api_key: str = ""
    default_llm_model: str = "pawn-agent"
    audio_transcription_model: Optional[str] = None
    tts_model: str = "tts-1"
    tts_voice: str = "af_heart"
    tts_language: str = "en"
    tts_speed: float = 1.0
    tts_format: str = "opus"
    llm_models: list[str] = Field(default_factory=lambda: ["pawn-agent"])
    default_prompt: str = (
        "You are Bob the chatbot and you are able to have normal interactions"
    )
    default_context_length: int = 1500


class MatrixSettings(BaseModel):
    user_id: str = "@bot:matrix.org"
    user_password: Optional[str] = None
    user_token: Optional[str] = None
    device_id: str = "DEVICE_ID"
    device_name: str = "nio-template"
    homeserver_url: str = "https://matrix.org"
    command_prefix: str = "!c "
    inviters: list[str] = Field(default_factory=list)
    power_users: list[str] = Field(default_factory=list)


class ConfigurationSettings(BaseModel):
    name: str = "default"


class BobSettings(BaseSettings):
    """
    Typed bootstrap settings loaded from local YAML.

    `BaseSettings` keeps env-var override support for CI/deploy use-cases while
    YAML remains the primary local source.
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
    )

    storage: StorageSettings = Field(default_factory=StorageSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    matrix: MatrixSettings = Field(default_factory=MatrixSettings)
    configuration: ConfigurationSettings = Field(default_factory=ConfigurationSettings)

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Backward compatibility: old configs used top-level `command_prefix`.
        command_prefix = data.get("command_prefix")
        if command_prefix is not None:
            matrix_cfg = data.setdefault("matrix", {})
            if isinstance(matrix_cfg, dict):
                matrix_cfg.setdefault("command_prefix", command_prefix)
        return data

    @classmethod
    def from_yaml(cls, config_file_path: str | Path) -> "BobSettings":
        path = Path(config_file_path).expanduser().resolve()
        with path.open(encoding="utf-8") as file_stream:
            yaml_payload = yaml.safe_load(file_stream.read()) or {}

        if not isinstance(yaml_payload, dict):
            raise ValueError(f"Config file '{path}' must contain a YAML object")

        return cls(**yaml_payload)

    @property
    def database_connection_string(self) -> str:
        return self.storage.database

    @property
    def configuration_name(self) -> str:
        return self.configuration.name

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="python")

    def to_runtime_flat_dict(self) -> Dict[str, Any]:
        runtime_payload = {
            "storage": self.storage.model_dump(mode="python"),
            "openai": self.openai.model_dump(mode="python"),
            "matrix": self.matrix.model_dump(mode="python"),
        }
        return _flatten_dict(runtime_payload)
