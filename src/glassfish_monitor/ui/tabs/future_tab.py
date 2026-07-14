"""Placeholder para futuras abas."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from glassfish_monitor.ui.styles.themes import Colors


class FutureTab(QWidget):
    """Aba placeholder para funcionalidades futuras."""

    def __init__(self, title: str = "Em Desenvolvimento", parent=None) -> None:
        super().__init__(parent)
        self._title = title
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface da aba."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("🚧")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel("Esta funcionalidade está em desenvolvimento.\nEm breve estará disponível.")
        desc_label.setStyleSheet(f"""
            font-size: 14px;
            color: {Colors.TEXT_SECONDARY};
            margin-top: 10px;
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)
