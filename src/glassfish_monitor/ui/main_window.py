"""Janela principal da aplicação GlassFish Monitor."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from glassfish_monitor.services.glassfish_service import GlassFishService, ServerStatus
from glassfish_monitor.services.mysql_service import MySQLService, MySQLStatus
from glassfish_monitor.services.postgres_service import PostgresService, PostgresStatus
from glassfish_monitor.ui.styles.themes import GlassFishStyles
from glassfish_monitor.ui.tabs.database_tab import DatabaseTab
from glassfish_monitor.ui.tabs.glassfish_tab import GlassFishTab


class MainWindow(QMainWindow):
    """Janela principal da aplicação."""

    def __init__(self) -> None:
        super().__init__()
        self._gf_service = GlassFishService()
        self._mysql_service = MySQLService()
        self._postgres_service = PostgresService()
        self._tabs: list[tuple[QWidget, object]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Ambiente de Desenvolvimento")
        self.setMinimumSize(QSize(1100, 700))
        self.resize(1200, 800)
        self.setStyleSheet(GlassFishStyles.get_stylesheet())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)

        self._glassfish_tab = GlassFishTab(self._gf_service)
        self._tab_widget.addTab(self._glassfish_tab, "GlassFish")
        self._tabs.append((self._glassfish_tab, self._gf_service))

        self._mysql_tab = DatabaseTab(
            service_name="MySQL",
            service=self._mysql_service,
            status_enum_running=MySQLStatus.RUNNING,
            status_enum_stopped=MySQLStatus.STOPPED,
            port=3306,
            admin_url="http://localhost:3306",
        )
        self._tab_widget.addTab(self._mysql_tab, "MySQL")
        self._tabs.append((self._mysql_tab, self._mysql_service))

        self._postgres_tab = DatabaseTab(
            service_name="PostgreSQL",
            service=self._postgres_service,
            status_enum_running=PostgresStatus.RUNNING,
            status_enum_stopped=PostgresStatus.STOPPED,
            port=5432,
            admin_url="http://localhost:5432",
        )
        self._tab_widget.addTab(self._postgres_tab, "PostgreSQL")
        self._tabs.append((self._postgres_tab, self._postgres_service))

        self._tab_widget.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tab_widget)

        self._setup_status_bar()

    def _setup_status_bar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._server_info = QLabel("Ambiente de Desenvolvimento")
        self._server_info.setStyleSheet("padding: 2px 10px;")
        self._status_bar.addWidget(self._server_info)

    def _on_tab_changed(self, index: int) -> None:
        for i, (tab, service) in enumerate(self._tabs):
            if i == index:
                tab.initialize()
            else:
                tab.shutdown()

    def initialize(self) -> None:
        for tab, _ in self._tabs:
            tab.initialize()

    def closeEvent(self, event) -> None:
        for tab, _ in self._tabs:
            tab.shutdown()
        event.accept()
