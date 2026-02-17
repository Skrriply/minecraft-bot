from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DISCORD_TOKEN: str
    DISCORD_OWNER_ID: int

    WORK_DIR: Path = Path(__file__).parent
    COGS_DIR: Path = WORK_DIR / "cogs"

    class Config:
        env_file = ".env"


settings = Settings()  # pyright: ignore
