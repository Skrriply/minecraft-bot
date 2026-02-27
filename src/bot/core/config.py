from pathlib import Path
from typing import TypeVar

from pydantic_settings import BaseSettings

T = TypeVar("T")


class Settings(BaseSettings):
    """Сlass for bot settings."""

    # Discord
    DISCORD_TOKEN: str
    DISCORD_OWNER_ID: int

    # Proxmox
    PROXMOX_URL: str
    PROXMOX_NODE: str
    PROXMOX_USER: str
    PROXMOX_TOKEN_ID: str
    PROXMOX_TOKEN_SECRET: str

    # Pterodactyl
    PTERODACTYL_URL: str
    PTERODACTYL_API_KEY: str
    PTERODACTYL_SERVER_ID: str

    # Dirs
    WORK_DIR: Path = Path(__file__).resolve().parent.parent
    COGS_DIR: Path = WORK_DIR / "cogs"
    LOGS_DIR: Path = WORK_DIR / "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()  # pyright: ignore
