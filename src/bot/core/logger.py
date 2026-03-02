from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def setup_logging(logs_dir: Path) -> None:
    """
    Configures the root logger.

    Args:
        logs_dir: The directory path where log files will be stored.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Creates the logs directory if it doesn't exist
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)

    # File handler
    file_handler = RotatingFileHandler(
        filename=logs_dir / "bot.log",
        mode="a",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
