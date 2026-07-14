"""Utilitários da plataforma."""

import platform
import os
from dataclasses import dataclass


@dataclass
class SystemInfo:
    """Informações do sistema."""

    os_name: str
    os_version: str
    python_version: str
    machine_name: str
    processor: str


def get_system_info() -> SystemInfo:
    """Obtém informações do sistema."""
    return SystemInfo(
        os_name=platform.system(),
        os_version=platform.version(),
        python_version=platform.python_version(),
        machine_name=platform.node(),
        processor=platform.processor() or "N/A",
    )


def get_glassfish_home_from_env() -> str | None:
    """Obtém o caminho do GLASSFISH_HOME da variável de ambiente."""
    return os.environ.get("GLASSFISH_HOME")


def is_windows() -> bool:
    """Verifica se o sistema é Windows."""
    return platform.system() == "Windows"


def is_linux() -> bool:
    """Verifica se o sistema é Linux."""
    return platform.system() == "Linux"


def is_macos() -> bool:
    """Verifica se o sistema é macOS."""
    return platform.system() == "Darwin"
