"""Módulo de inicialização da aplicação GlassFish Monitor."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from glassfish_monitor.config import GlassFishConfig
from glassfish_monitor.ui.main_window import MainWindow
from glassfish_monitor.utils.logger import setup_logger


def create_app(sys_argv: list[str]) -> QApplication:
    """Cria e configura a aplicação Qt."""
    app = QApplication(sys_argv)
    app.setApplicationName("GlassFish Monitor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("GlassFish Monitor")
    app.setStyle("Fusion")

    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)

    return app


def run() -> int:
    """Executa a aplicação."""
    log_dir = Path.home() / ".glassfish_monitor" / "logs"
    setup_logger(log_dir)

    app = create_app(sys.argv)

    window = MainWindow()
    window.show()

    window.initialize()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
