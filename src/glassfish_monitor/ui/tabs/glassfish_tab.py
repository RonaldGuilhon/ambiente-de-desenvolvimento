"""Aba principal de monitoramento do GlassFish."""

import webbrowser

from loguru import logger
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from glassfish_monitor.config import GlassFishConfig
from glassfish_monitor.services.glassfish_service import (
    DeployedApp,
    GlassFishService,
    ServerStatus,
)
from glassfish_monitor.ui.styles.themes import Colors
from glassfish_monitor.ui.widgets.status_widget import StatusWidget


class InfoCard(QFrame):
    """Card de informações."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            InfoCard {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        self._title = QLabel(title)
        self._title.setStyleSheet(f"""
            font-size: 13px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        layout.addWidget(self._title)

        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(4)
        layout.addLayout(self._content_layout)

    def add_row(self, label: str, value: str, clickable: bool = False) -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(f"{label}:")
        lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        lbl.setFixedWidth(120)
        row.addWidget(lbl)

        val = QLabel(value)
        if clickable:
            val.setStyleSheet(f"""
                color: {Colors.PRIMARY_LIGHT};
                font-size: 12px;
                text-decoration: underline;
            """)
            val.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            val.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px;")
        row.addWidget(val)
        row.addStretch()

        self._content_layout.addLayout(row)
        return val

    def add_separator(self) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {Colors.BORDER}; max-height: 1px;")
        self._content_layout.addWidget(line)

    def clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()


class GlassFishTab(QWidget):
    """Aba de monitoramento e controle do GlassFish."""

    def __init__(self, glassfish_service: GlassFishService, parent=None) -> None:
        super().__init__(parent)
        self._gf_service = glassfish_service
        self._is_starting = False
        self._is_stopping = False
        self._admin_url = f"http://localhost:{GlassFishConfig.ADMIN_PORT}"
        self._http_url = f"http://localhost:{GlassFishConfig.HTTP_PORT}"
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        header = QHBoxLayout()
        title = QLabel("GlassFish Server")
        title.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        header.addWidget(title)
        header.addStretch()

        self._version_label = QLabel("")
        self._version_label.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_SECONDARY};
        """)
        header.addWidget(self._version_label)
        main_layout.addLayout(header)

        self._status_widget = StatusWidget()
        main_layout.addWidget(self._status_widget)

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
        self._start_button.clicked.connect(self._on_start_clicked)
        controls_layout.addWidget(self._start_button)

        self._stop_button = QPushButton("Parar")
        self._stop_button.setObjectName("stopButton")
        self._stop_button.setMinimumHeight(36)
        self._stop_button.setMinimumWidth(110)
        self._stop_button.clicked.connect(self._on_stop_clicked)
        controls_layout.addWidget(self._stop_button)

        self._restart_button = QPushButton("Reiniciar")
        self._restart_button.setObjectName("restartButton")
        self._restart_button.setMinimumHeight(36)
        self._restart_button.setMinimumWidth(110)
        self._restart_button.clicked.connect(self._on_restart_clicked)
        controls_layout.addWidget(self._restart_button)

        self._refresh_button = QPushButton("Atualizar")
        self._refresh_button.setMinimumHeight(36)
        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        controls_layout.addWidget(self._refresh_button)

        controls_layout.addStretch()

        self._operation_label = QLabel("")
        self._operation_label.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.WARNING};
            font-weight: bold;
        """)
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

        self._ports_card = InfoCard("Portas")
        self._ports_card.add_row("Admin", str(GlassFishConfig.ADMIN_PORT))
        self._ports_card.add_row("HTTP", str(GlassFishConfig.HTTP_PORT))
        self._ports_card.add_row("HTTPS", str(GlassFishConfig.HTTPS_PORT))
        info_layout.addWidget(self._ports_card)

        self._links_card = InfoCard("Links")
        self._admin_link = self._links_card.add_row(
            "Admin Console", self._admin_url, clickable=True
        )
        self._admin_link.mousePressEvent = lambda _: webbrowser.open(self._admin_url)

        self._http_link = self._links_card.add_row(
            "Aplicações", self._http_url, clickable=True
        )
        self._http_link.mousePressEvent = lambda _: webbrowser.open(self._http_url)
        info_layout.addWidget(self._links_card)

        content_layout.addLayout(info_layout)

        self._apps_card = InfoCard("Aplicações Deployadas")
        self._apps_table = QTableWidget()
        self._apps_table.setColumnCount(3)
        self._apps_table.setHorizontalHeaderLabels(["Nome", "Context Root", "Status"])
        self._apps_table.horizontalHeader().setStretchLastSection(True)
        self._apps_table.horizontalHeader().setSectionResizeMode(0, self._apps_table.horizontalHeader().ResizeMode.Stretch)
        self._apps_table.horizontalHeader().setSectionResizeMode(1, self._apps_table.horizontalHeader().ResizeMode.Stretch)
        self._apps_table.verticalHeader().setVisible(False)
        self._apps_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._apps_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._apps_table.setAlternatingRowColors(True)
        self._apps_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                gridline-color: {Colors.BORDER};
            }}
            QTableWidget::item {{
                padding: 6px;
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY_DARK};
            }}
            QHeaderView::section {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                padding: 6px;
                border: 1px solid {Colors.BORDER};
                font-weight: bold;
            }}
        """)
        self._apps_table.setMinimumHeight(150)
        self._apps_card._content_layout.addWidget(self._apps_table)
        content_layout.addWidget(self._apps_card)

        content_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        self._update_buttons_state(ServerStatus.UNKNOWN)

    def _connect_signals(self) -> None:
        self._gf_service.status_changed.connect(self._on_status_changed)
        self._gf_service.command_executed.connect(self._on_command_executed)
        self._gf_service.error_occurred.connect(self._on_error_occurred)

    def initialize(self) -> None:
        valid, message = self._gf_service.validate_installation()
        if valid:
            lines = message.split("\n")
            for line in lines:
                if line.startswith("GlassFish"):
                    self._version_label.setText(line.replace("GlassFish encontrado em: ", ""))

        self._gf_service.check_status_async()

    def shutdown(self) -> None:
        pass

    def _refresh_apps(self) -> None:
        if self._gf_service.current_status != ServerStatus.RUNNING:
            self._apps_table.setRowCount(0)
            return

        apps = self._gf_service.list_deployed_apps()
        self._on_apps_loaded(apps)

    def _on_apps_loaded(self, apps: list[DeployedApp]) -> None:
        self._apps_table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            name_item = QTableWidgetItem(app.name)
            root_item = QTableWidgetItem(app.context_root)
            status_item = QTableWidgetItem(app.status)

            if app.status == "disabled":
                status_item.setForeground(self._status_widget._indicator.palette().color(
                    self._status_widget._indicator.foregroundRole()
                ))

            self._apps_table.setItem(i, 0, name_item)
            self._apps_table.setItem(i, 1, root_item)
            self._apps_table.setItem(i, 2, status_item)

        self._apps_table.resizeColumnsToContents()

    def _update_buttons_state(self, status: ServerStatus) -> None:
        is_running = status == ServerStatus.RUNNING
        is_operation_running = self._is_starting or self._is_stopping

        self._start_button.setEnabled(not is_running and not is_operation_running)
        self._stop_button.setEnabled(is_running and not is_operation_running)
        self._restart_button.setEnabled(is_running and not is_operation_running)
        self._refresh_button.setEnabled(not is_operation_running)

        if is_operation_running:
            self._operation_label.setText(
                "Iniciando..." if self._is_starting else "Parando..."
            )
        else:
            self._operation_label.setText("")

    @Slot()
    def _on_start_clicked(self) -> None:
        self._is_starting = True
        self._update_buttons_state(self._gf_service.current_status)
        self._gf_service.start_domain()

    @Slot()
    def _on_stop_clicked(self) -> None:
        self._is_stopping = True
        self._update_buttons_state(self._gf_service.current_status)
        self._gf_service.stop_domain()

    @Slot()
    def _on_restart_clicked(self) -> None:
        self._is_stopping = True
        self._update_buttons_state(self._gf_service.current_status)
        self._gf_service.restart_domain()

    @Slot()
    def _on_refresh_clicked(self) -> None:
        self._gf_service.check_status_async()
        self._refresh_apps()

    @Slot(ServerStatus)
    def _on_status_changed(self, status: ServerStatus) -> None:
        self._is_starting = False
        self._is_stopping = False
        self._status_widget.update_status(status)
        self._update_buttons_state(status)

        if status == ServerStatus.RUNNING:
            self._refresh_apps()
        elif status == ServerStatus.STOPPED:
            self._apps_table.setRowCount(0)

    @Slot(str, bool)
    def _on_command_executed(self, command: str, success: bool) -> None:
        self._is_starting = False
        self._is_stopping = False
        self._update_buttons_state(self._gf_service.current_status)

        if command in ("start-domain", "restart-domain") and success:
            self._refresh_apps()

    @Slot(str)
    def _on_error_occurred(self, error: str) -> None:
        self._is_starting = False
        self._is_stopping = False
        self._update_buttons_state(self._gf_service.current_status)
