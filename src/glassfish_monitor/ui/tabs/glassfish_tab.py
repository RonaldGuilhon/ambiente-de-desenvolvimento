"""Aba principal de monitoramento do GlassFish."""

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from glassfish_monitor.config import GlassFishConfig
from glassfish_monitor.services.glassfish_service import GlassFishService, ServerStatus
from glassfish_monitor.services.monitor_service import MonitorService, ResourceMetrics
from glassfish_monitor.ui.styles.themes import Colors
from glassfish_monitor.ui.widgets.log_viewer import LogViewer
from glassfish_monitor.ui.widgets.metrics_panel import MetricsPanel
from glassfish_monitor.ui.widgets.status_widget import StatusWidget


class GlassFishTab(QWidget):
    """Aba de monitoramento e controle do GlassFish."""

    def __init__(self, glassfish_service: GlassFishService, parent=None) -> None:
        super().__init__(parent)
        self._gf_service = glassfish_service
        self._monitor_service = MonitorService(glassfish_service)
        self._is_starting = False
        self._is_stopping = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Configura a interface da aba."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        header_layout = QHBoxLayout()

        title = QLabel("GlassFish Server")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._version_label = QLabel("GlassFish 4.1.1")
        self._version_label.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_SECONDARY};
        """)
        header_layout.addWidget(self._version_label)

        main_layout.addLayout(header_layout)

        self._status_widget = StatusWidget()
        main_layout.addWidget(self._status_widget)

        controls_group = QFrame()
        controls_group.setFrameShape(QFrame.Shape.StyledPanel)
        controls_group.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        controls_layout = QHBoxLayout(controls_group)
        controls_layout.setSpacing(10)

        self._start_button = QPushButton("Iniciar")
        self._start_button.setObjectName("startButton")
        self._start_button.setMinimumHeight(40)
        self._start_button.setMinimumWidth(120)
        self._start_button.clicked.connect(self._on_start_clicked)
        controls_layout.addWidget(self._start_button)

        self._stop_button = QPushButton("Parar")
        self._stop_button.setObjectName("stopButton")
        self._stop_button.setMinimumHeight(40)
        self._stop_button.setMinimumWidth(120)
        self._stop_button.clicked.connect(self._on_stop_clicked)
        controls_layout.addWidget(self._stop_button)

        self._restart_button = QPushButton("Reiniciar")
        self._restart_button.setObjectName("restartButton")
        self._restart_button.setMinimumHeight(40)
        self._restart_button.setMinimumWidth(120)
        self._restart_button.clicked.connect(self._on_restart_clicked)
        controls_layout.addWidget(self._restart_button)

        controls_layout.addSpacing(20)

        self._refresh_button = QPushButton("Atualizar Status")
        self._refresh_button.setMinimumHeight(40)
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

        main_layout.addWidget(controls_group)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._metrics_panel = MetricsPanel()
        splitter.addWidget(self._metrics_panel)

        self._log_viewer = LogViewer()
        splitter.addWidget(self._log_viewer)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

        self._update_buttons_state(ServerStatus.UNKNOWN)

    def _connect_signals(self) -> None:
        """Conecta os sinais dos serviços."""
        self._gf_service.status_changed.connect(self._on_status_changed)
        self._gf_service.command_executed.connect(self._on_command_executed)
        self._gf_service.error_occurred.connect(self._on_error_occurred)
        self._gf_service.log_message.connect(self._on_log_message)

        self._monitor_service.metrics_updated.connect(self._on_metrics_updated)
        self._monitor_service.history_updated.connect(self._on_history_updated)

        self._status_widget.status_changed.connect(self._on_status_widget_changed)

    def initialize(self) -> None:
        """Inicializa a aba - chamado quando a aba é selecionada."""
        valid, message = self._gf_service.validate_installation()
        if not valid:
            self._log_viewer.append_log_line(f"[AVISO] {message}")

        log_path = GlassFishConfig.get_domain_log_path()
        if log_path.exists():
            self._log_viewer.set_log_path(log_path)

        self._gf_service.check_status_async()
        self._monitor_service.start_monitoring()

    def shutdown(self) -> None:
        """Desliga a aba - chamado quando a aba é desselecionada."""
        self._monitor_service.stop_monitoring()
        self._gf_service.cancel_all_operations()

    def _update_buttons_state(self, status: ServerStatus) -> None:
        """Atualiza o estado dos botões baseado no status."""
        is_running = status == ServerStatus.RUNNING
        is_operation_running = self._is_starting or self._is_stopping

        self._start_button.setEnabled(not is_running and not is_operation_running)
        self._stop_button.setEnabled(is_running and not is_operation_running)
        self._restart_button.setEnabled(is_running and not is_operation_running)
        self._refresh_button.setEnabled(not is_operation_running)

        if is_operation_running:
            if self._is_starting:
                self._operation_label.setText("Iniciando servidor...")
            elif self._is_stopping:
                self._operation_label.setText("Parando servidor...")
        else:
            self._operation_label.setText("")

    @Slot()
    def _on_start_clicked(self) -> None:
        """Callback do botão iniciar."""
        self._is_starting = True
        self._update_buttons_state(self._gf_service.current_status)
        self._gf_service.start_domain()

    @Slot()
    def _on_stop_clicked(self) -> None:
        """Callback do botão parar."""
        self._is_stopping = True
        self._update_buttons_state(self._gf_service.current_status)
        self._gf_service.stop_domain()

    @Slot()
    def _on_restart_clicked(self) -> None:
        """Callback do botão reiniciar."""
        self._is_stopping = True
        self._update_buttons_state(self._gf_service.current_status)
        self._gf_service.restart_domain()

    @Slot()
    def _on_refresh_clicked(self) -> None:
        """Callback do botão atualizar."""
        self._gf_service.check_status_async()

    @Slot(ServerStatus)
    def _on_status_changed(self, status: ServerStatus) -> None:
        """Callback quando o status muda."""
        self._is_starting = False
        self._is_stopping = False
        self._status_widget.update_status(status)
        self._update_buttons_state(status)

    @Slot(str, bool)
    def _on_command_executed(self, command: str, success: bool) -> None:
        """Callback quando um comando é executado."""
        self._is_starting = False
        self._is_stopping = False
        self._update_buttons_state(self._gf_service.current_status)

        if success:
            self._log_viewer.append_log_line(f"[SUCESSO] Comando '{command}' executado com sucesso")
        else:
            self._log_viewer.append_log_line(f"[FALHA] Comando '{command}' falhou")

    @Slot(str)
    def _on_error_occurred(self, error: str) -> None:
        """Callback quando ocorre um erro."""
        self._is_starting = False
        self._is_stopping = False
        self._update_buttons_state(self._gf_service.current_status)
        self._log_viewer.append_log_line(f"[ERRO] {error}")

    @Slot(ServerStatus)
    def _on_status_widget_changed(self, status: ServerStatus) -> None:
        """Callback quando o status widget muda."""
        self._update_buttons_state(status)

    @Slot(ResourceMetrics)
    def _on_metrics_updated(self, metrics: ResourceMetrics) -> None:
        """Callback quando as métricas são atualizadas."""
        self._metrics_panel.update_metrics(metrics)

    @Slot()
    def _on_history_updated(self) -> None:
        """Callback quando o histórico é atualizado."""
        self._metrics_panel.update_graphs(self._monitor_service.history)

    @Slot(str)
    def _on_log_message(self, message: str) -> None:
        """Callback para mensagens de log."""
        self._log_viewer.append_log_line(message)
