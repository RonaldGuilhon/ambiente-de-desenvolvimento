"""Janela principal da aplicação GlassFish Monitor."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from glassfish_monitor.services.glassfish_service import GlassFishService, ServerStatus
from glassfish_monitor.ui.styles.themes import GlassFishStyles
from glassfish_monitor.ui.tabs.future_tab import FutureTab
from glassfish_monitor.ui.tabs.glassfish_tab import GlassFishTab


class MainWindow(QMainWindow):
    """Janela principal da aplicação."""

    def __init__(self) -> None:
        super().__init__()
        self._gf_service = GlassFishService()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Configura a interface da janela principal."""
        self.setWindowTitle("GlassFish Monitor v1.0.0")
        self.setMinimumSize(QSize(1200, 800))
        self.resize(1400, 900)

        self.setStyleSheet(GlassFishStyles.get_stylesheet())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)

        self._glassfish_tab = GlassFishTab(self._gf_service)
        self._tab_widget.addTab(self._glassfish_tab, "GlassFish Server")

        self._tab_widget.addTab(FutureTab("Deploy & Gerenciamento"), "Deploy")
        self._tab_widget.addTab(FutureTab("Configurações"), "Configurações")
        self._tab_widget.addTab(FutureTab("Logs Avançados"), "Logs")

        self._tab_widget.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tab_widget)

        self._setup_status_bar()

    def _setup_status_bar(self) -> None:
        """Configura a barra de status."""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._connection_status = QLabel("GlassFish Monitor")
        self._connection_status.setStyleSheet("padding: 2px 10px;")
        self._status_bar.addWidget(self._connection_status)

        self._server_info = QLabel("")
        self._server_info.setStyleSheet("padding: 2px 10px; color: #B0B0B0;")
        self._status_bar.addPermanentWidget(self._server_info)

    def _connect_signals(self) -> None:
        """Conecta os sinais."""
        self._gf_service.status_changed.connect(self._on_status_changed)

    def initialize(self) -> None:
        """Inicializa a aplicação."""
        self._glassfish_tab.initialize()
        self._update_server_info()

    def _on_tab_changed(self, index: int) -> None:
        """Callback quando a aba é alterada."""
        if index == 0:
            self._glassfish_tab.initialize()
        else:
            self._glassfish_tab.shutdown()

    def _on_status_changed(self, status: ServerStatus) -> None:
        """Callback quando o status muda."""
        status_text = {
            ServerStatus.RUNNING: "Servidor Ativo",
            ServerStatus.STOPPED: "Servidor Parado",
            ServerStatus.RESTART_REQUIRED: "Reinício Necessário",
            ServerStatus.UNKNOWN: "Verificando...",
            ServerStatus.ERROR: "Erro de Conexão",
        }
        self._connection_status.setText(status_text.get(status, "Desconhecido"))

    def _update_server_info(self) -> None:
        """Atualiza as informações do servidor na barra de status."""
        version = self._gf_service.get_version()
        if version:
            self._server_info.setText(
                f"{version.product_name} | Porta: {self._gf_service.domain_name}"
            )
        else:
            self._server_info.setText(f"Domínio: {self._gf_service.domain_name}")

    def closeEvent(self, event) -> None:
        """Trata o evento de fechamento da janela."""
        self._glassfish_tab.shutdown()
        event.accept()
