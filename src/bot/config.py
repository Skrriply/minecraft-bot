from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Discord
    DISCORD_TOKEN: str
    DISCORD_OWNER_ID: int
    DISCORD_CHANNEL_ID: int

    # Pterodactyl
    PTERODACTYL_URL: str
    PTERODACTYL_API_KEY: str
    PTERODACTYL_SERVER_ID: str

    # Proxmox
    PROXMOX_URL: str
    PROXMOX_NODE: str
    PROXMOX_USER: str
    PROXMOX_TOKEN_ID: str
    PROXMOX_TOKEN_SECRET: str

    # Svitlo.live API
    OUTAGE_API_URL: str
    REGION_CPU: str = "kyiv"
    GROUP_ID: str = "1.1"

    # Other settings
    CACHE_TTL_MINUTES: int = 10
    SHUTDOWN_OFFSET_MINUTES: int = 10
    WARN_OFFSET_MINUTES: int = 5
    STARTUP_TIMEOUT_SECONDS: int = 300
    STOP_TIMEOUT_SECONDS: int = 300
    TIMEZONE: str = "Europe/Kyiv"

    WORK_DIR: Path = Path(__file__).parent
    COGS_DIR: Path = WORK_DIR / "cogs"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()  # pyright: ignore
