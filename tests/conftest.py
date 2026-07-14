"""Configurações de teste do pytest."""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp_instance():
    """Cria uma instância do QApplication para testes."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
