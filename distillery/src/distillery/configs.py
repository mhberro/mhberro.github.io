# Copyright 2026 Lockheed Martin Corporation
# Lockheed Martin Proprietary Information

"""Configuration container for Distillery."""

import logging
import os
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import Parameter
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

logger = logging.getLogger(__name__)


class Configs(BaseSettings):
    """Configuration container/loader."""

    log_level: Annotated[
        Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], Parameter(alias="-l")
    ] = Field(
        description="Specify the logging threshold.",
        default="INFO",
    )
    playlist_id: str = Field(description="A YouTube playlist ID.")
    playlist_name: str | None = Field(
        description="Optional playlist name used to create an output subdirectory.",
        default=None,
    )
    youtube_api_key: SecretStr = Field(
        description="A personal access key for accessing the YouTube API."
        " Falls back to YOUTUBE_API_KEY when not passed by CLI/config.",
        validation_alias=AliasChoices(
            "youtube_api_key", "youtube_api_token", "YOUTUBE_API_KEY"
        ),
    )
    output: Path = Field(
        description="an output directory for video transcript markdown files.",
        default=Path("transcripts"),
    )
    dry_run: bool = Field(
        description="Only list transcript files that would be generated.",
        default=False,
    )
    model: str = Field(
        default="gemma-4-26b-a4b-it",
        description="Specify an LLM model to use for distilling",
    )
    api_base_url: str = Field(
        description="Specify an AI Factory LLM API URL to use.",
        default="https://api.ai.us.lmco.com/v1",
    )

    model_config = SettingsConfigDict(
        arbitrary_types_allowed=True,
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_prefix="distillery_",
        yaml_file=os.getenv("DISTILLERY_CONFIG_PATH", "distillery.yaml"),
    )

    @classmethod
    def settings_customise_sources(  # noqa: PLR0913
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define custom configurations source settings."""
        return (
            file_secret_settings,
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )

    def summary(self) -> None:
        """Display loaded configs to console."""
        loader = "[dodger_blue2]Config Loader[/dodger_blue2]"
        logger.info(
            "[spring_green3]Beginning Rosalina with the"
            " following configurations:[/spring_green3]"
        )

        title_case_attrs: dict[str, str] = {}
        buffer = 0
        for attr in vars(self):
            title_case_attrs[attr] = " ".join([p.capitalize() for p in attr.split("_")])
            buffer = max(buffer, len(title_case_attrs[attr]))

        for attr, value in vars(self).items():
            spacing = " " * (buffer - len(title_case_attrs[attr]))
            logger.info(
                "    * %s - %s%s : %s", loader, title_case_attrs[attr], spacing, value
            )
