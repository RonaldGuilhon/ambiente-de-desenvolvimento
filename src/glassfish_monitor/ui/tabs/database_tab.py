"""Aba genérica de gerenciamento de banco de dados."""

import webbrowser

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from glassfish_monitor.ui.styles.themes import Colors
from glassfish_monitor.ui.widgets.status_widget import StatusIndicator


class DatabaseTab(QWidget):
    """Aba genérica para gerenciamento de bancos de dados."""

    def __init__(
        self,
        service_name: str,
        service,
        status_enum_running,
        status_enum_stopped,
        port: int = 3306,
        admin_url: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service_name = service_name
        self._service = service
        self._status_running = status_enum_running
        self._status_stopped = status_enum_stopped
        self._port = port
        self._admin_url = admin_url
        self._is_starting = False
        self._is_stopping = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        header = QHBoxLayout()
        title = QLabel(self._service_name)
        title.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        header.addWidget(title)
        header.addStretch()

        self._version_label = QLabel("")
        self._version_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY};")
        header.addWidget(self._version_label)
        main_layout.addLayout(header)

        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 10, 15, 10)
        status_layout.setSpacing(15)

        self._indicator = StatusIndicator(20)
        status_layout.addWidget(self._indicator)

        status_info = QVBoxLayout()
        status_info.setSpacing(2)
        self._status_label = QLabel("Status: Verificando...")
        self._status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        status_info.addWidget(self._status_label)
        self._detail_label = QLabel("Aguardando verificação...")
        self._detail_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        status_info.addWidget(self._detail_label)
        status_layout.addLayout(status_info)
        status_layout.addStretch()

        main_layout.addWidget(status_frame)

        controls = QFrame()
        controls.setFrameShape(QFrame.Shape.StyledPanel)
        controls.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(12, 8, 12, 8)
        controls_layout.setSpacing(10)

        self._start_button = QPushButton("Iniciar")
        self._start_button.setObjectName("startButton")
        self._start_button.setMinimumHeight(36)
        self._start_button.setMinimumWidth(110)
        self._start_button.clicked.connect(self._on_start)
        controls_layout.addWidget(self._start_button)

        self._stop_button = QPushButton("Parar")
        self._stop_button.setObjectName("stopButton")
        self._stop_button.setMinimumHeight(36)
        self._stop_button.setMinimumWidth(110)
        self._stop_button.clicked.connect(self._on_stop)
        controls_layout.addWidget(self._stop_button)

        self._restart_button = QPushButton("Reiniciar")
        self._restart_button.setObjectName("restartButton")
        self._restart_button.setMinimumHeight(36)
        self._restart_button.setMinimumWidth(110)
        self._restart_button.clicked.connect(self._on_restart)
        controls_layout.addWidget(self._restart_button)

        self._refresh_button = QPushButton("Atualizar")
        self._refresh_button.setMinimumHeight(36)
        self._refresh_button.clicked.connect(self._on_refresh)
        controls_layout.addWidget(self._refresh_button)

        controls_layout.addStretch()

        self._operation_label = QLabel("")
        self._operation_label.setStyleSheet(f"font-size: 12px; color: {Colors.WARNING}; font-weight: bold;")
        controls_layout.addWidget(self._operation_label)

        main_layout.addWidget(controls)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(12)

        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)

        port_card = QFrame()
        port_card.setFrameShape(QFrame.Shape.StyledPanel)
        port_card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        port_inner = QVBoxLayout(port_card)
        port_title = QLabel("Porta")
        port_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.PRIMARY};")
        port_inner.addWidget(port_title)
        port_val = QLabel(str(self._port))
        port_val.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        port_inner.addWidget(port_val)
        port_inner.addStretch()
        info_layout.addWidget(port_card)

        if self._admin_url:
            link_card = QFrame()
            link_card.setFrameShape(QFrame.Shape.StyledPanel)
            link_card.setStyleSheet(port_card.styleSheet())
            link_inner = QVBoxLayout(link_card)
            link_title = QLabel("Link")
            link_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.PRIMARY};")
            link_inner.addWidget(link_title)
            link_val = QLabel(self._admin_url)
            link_val.setStyleSheet(f"""
                font-size: 12px;
                color: {Colors.PRIMARY_LIGHT};
                text-decoration: underline;
            """)
            link_val.setCursor(Qt.CursorShape.PointingHandCursor)
            link_val.mousePressEvent = lambda _: webbrowser.open(self._admin_url)
            link_inner.addWidget(link_val)
            link_inner.addStretch()
            info_layout.addWidget(link_card)

        info_layout.addStretch()
        content_layout.addLayout(info_layout)
        content_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _connect_signals(self) -> None:
        self._service.status_changed.connect(self._on_status_changed)
        self._service.command_executed.connect(self._on_command_executed)
        self._service.error_occurred.connect(self._on_error)
        if hasattr(self._service, 'info_loaded'):
            self._service.info_loaded.connect(self._on_info_loaded)

    def initialize(self) -> None:
        self._service.check_status_async()

    def shutdown(self) -> None:
        pass

    def _update_buttons(self, running: bool) -> None:
        busy = self._is_starting or self._is_stopping
        self._start_button.setEnabled(not running and not busy)
        self._stop_button.setEnabled(running and not busy)
        self._restart_button.setEnabled(running and not busy)
        self._refresh_button.setEnabled(not busy)

        if busy:
            self._operation_label.setText("Iniciando..." if self._is_starting else "Parando...")
        else:
            self._operation_label.setText("")

    def _set_status(self, running: bool, detail: str = "") -> None:
        color = Colors.SUCCESS if running else Colors.ERROR
        text = "Executando" if running else "Parado"
        self._indicator.set_color(color)
        self._status_label.setText(f"Status: {text}")
        self._status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        self._detail_label.setText(detail or f"Serviço {text.lower()}")

    def _on_info_loaded(self, info) -> None:
        if hasattr(info, 'version') and info.version:
            self._version_label.setText(info.version)

    @Slot()
    def _on_start(self) -> None:
        self._is_starting = True
        self._update_buttons(self._service.current_status == self._status_running)
        self._service.start()

    @Slot()
    def _on_stop(self) -> None:
        self._is_stopping = True
        self._update_buttons(self._service.current_status == self._status_running)
        self._service.stop()

    @Slot()
    def _on_restart(self) -> None:
        self._is_stopping = True
        self._update_buttons(self._service.current_status == self._status_running)
        self._service.restart()

    @Slot()
    def _on_refresh(self) -> None:
        self._service.check_status_async()

    def _on_status_changed(self, status) -> None:
        self._is_starting = False
        self._is_stopping = False
        running = status == self._status_running
        self._set_status(running)
        self._update_buttons(running)

    def _on_command_executed(self, command: str, success: bool) -> None:
        self._is_starting = False
        self._is_stopping = False
        running = self._service.current_status == self._status_running
        self._set_status(running)
        self._update_buttons(running)

    def _on_error(self, msg: str) -> None:
        self._is_starting = False
        self._is_stopping = False
        self._indicator.set_color(Colors.ERROR)
        self._status_label.setText("Status: Erro")
        self._status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.ERROR};")
        self._detail_label.setText(msg[:100])
        self._update_buttons(False)
