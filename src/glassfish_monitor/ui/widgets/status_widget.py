"""Widget de status do servidor GlassFish."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from glassfish_monitor.services.glassfish_service import ServerStatus
from glassfish_monitor.ui.styles.themes import Colors


class StatusIndicator(QLabel):
    """Indicador visual de status com LED."""

    def __init__(self, size: int = 16, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self._color = Colors.TEXT_DISABLED
        self.setFixedSize(size, size)

    def set_color(self, color: str) -> None:
        """Define a cor do indicador."""
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:
        """Renderiza o indicador LED."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QColor(self._color))
        painter.setPen(QPen(QColor(self._color).darker(150), 1))
        painter.drawEllipse(1, 1, self._size - 2, self._size - 2)


class StatusWidget(QFrame):
    """Widget que exibe o status do servidor GlassFish."""

    status_changed = Signal(ServerStatus)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_status = ServerStatus.UNKNOWN
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do widget."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            StatusWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 10px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        self._indicator = StatusIndicator(20)
        layout.addWidget(self._indicator)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self._status_label = QLabel("Status: Desconhecido")
        self._status_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {Colors.TEXT_PRIMARY};
        """)
        info_layout.addWidget(self._status_label)

        self._detail_label = QLabel("Aguardando verificação...")
        self._detail_label.setStyleSheet(f"""
            font-size: 11px;
            color: {Colors.TEXT_SECONDARY};
        """)
        info_layout.addWidget(self._detail_label)

        layout.addLayout(info_layout)
        layout.addStretch()

    def update_status(self, status: ServerStatus) -> None:
        """Atualiza o status exibido."""
        self._current_status = status

        status_text = {
            ServerStatus.RUNNING: "Executando",
            ServerStatus.STOPPED: "Parado",
            ServerStatus.RESTART_REQUIRED: "Reinicialização Necessária",
            ServerStatus.UNKNOWN: "Desconhecido",
            ServerStatus.ERROR: "Erro",
        }

        detail_text = {
            ServerStatus.RUNNING: "O servidor está respondendo normalmente",
            ServerStatus.STOPPED: "O servidor está desligado",
            ServerStatus.RESTART_REQUIRED: "Alterações pendentes requerem reinício",
            ServerStatus.UNKNOWN: "Aguardando verificação...",
            ServerStatus.ERROR: "Falha ao verificar status do servidor",
        }

        color = Colors.get_status_indicator_color(status.value)

        self._indicator.set_color(color)
        self._status_label.setText(f"Status: {status_text.get(status, 'Desconhecido')}")
        self._detail_label.setText(detail_text.get(status, ""))

        self._status_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {color};
        """)

        self.status_changed.emit(status)

    def get_current_status(self) -> ServerStatus:
        """Retorna o status atual."""
        return self._current_status
