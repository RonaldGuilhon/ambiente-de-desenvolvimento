"""Sistema de logging do GlassFish Monitor."""

import sys
from pathlib import Path

from loguru import logger


def setup_logger(log_dir: Path | None = None, level: str = "DEBUG") -> None:
    """Configura o sistema de logging."""
    logger.remove()

    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=level,
        colorize=True,
    )

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "glassfish_monitor.log"
        logger.add(
            str(log_file),
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )

    logger.debug("Logger configurado com sucesso")
