import os
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv

T = TypeVar("T")

load_dotenv()


class Config:
    """Сlass for bot configuration."""

    def __init__(self) -> None:
        """Initializes the class."""
        # Discord
        self.DISCORD_TOKEN: str = self._get_env("DISCORD_TOKEN")
        self.DISCORD_OWNER_ID: int = int(self._get_env("DISCORD_OWNER_ID"))

        # Dirs
        WORK_DIR: Path = Path(__file__).resolve().parent.parent
        self.COGS_DIR: Path = WORK_DIR / "cogs"
        self.LOGS_DIR: Path = WORK_DIR / "logs"

    def _get_env(self, key: str, default: T | None = None) -> str | T:
        """
        Retrieves an environment variable by key.

        Args:
            key: The environment variable name.
            default (optional): The default value if the key is not found.

        Returns:
            str: The value of the environment variable.

        Raises:
            ValueError: If the environment variable is missing and no default is provided.
        """
        value = os.getenv(key, default)

        if value is None:
            raise ValueError(f"Error: Environment variable '{key}' not found!")

        return value


settings = Config()
