"""Serviço de monitoramento de recursos do GlassFish."""

import time
from collections import deque
from dataclasses import dataclass, field

import psutil
from loguru import logger
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from glassfish_monitor.config import GlassFishConfig
from glassfish_monitor.services.glassfish_service import GlassFishService, ServerStatus


@dataclass
class ResourceMetrics:
    """Métricas de recursos do sistema."""

    timestamp: float = 0.0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    threads: int = 0
    open_files: int = 0
    connections: int = 0
    thread_count: int = 0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class MetricsHistory:
    """Histórico de métricas para gráficos."""

    max_points: int = 300  # 5 minutos a cada 1s
    cpu: deque[float] = field(default_factory=lambda: deque(maxlen=300))
    memory: deque[float] = field(default_factory=lambda: deque(maxlen=300))
    memory_mb: deque[float] = field(default_factory=lambda: deque(maxlen=300))
    threads: deque[int] = field(default_factory=lambda: deque(maxlen=300))
    timestamps: deque[float] = field(default_factory=lambda: deque(maxlen=300))

    def add(self, metrics: ResourceMetrics) -> None:
        """Adiciona uma nova métrica ao histórico."""
        self.cpu.append(metrics.cpu_percent)
        self.memory.append(metrics.memory_percent)
        self.memory_mb.append(metrics.memory_mb)
        self.threads.append(metrics.threads)
        self.timestamps.append(metrics.timestamp)

    def clear(self) -> None:
        """Limpa o histórico."""
        self.cpu.clear()
        self.memory.clear()
        self.memory_mb.clear()
        self.threads.clear()
        self.timestamps.clear()


class MonitorService(QObject):
    """Serviço de monitoramento de recursos do GlassFish."""

    metrics_updated = Signal(ResourceMetrics)
    history_updated = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        glassfish_service: GlassFishService,
        interval_ms: int | None = None,
    ) -> None:
        super().__init__()
        self._gf_service = glassfish_service
        self._interval = interval_ms or GlassFishConfig.MONITOR_INTERVAL_MS
        self._is_monitoring = False
        self._history = MetricsHistory()
        self._current_pid: int | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._collect_metrics)

    @property
    def is_monitoring(self) -> bool:
        return self._is_monitoring

    @property
    def history(self) -> MetricsHistory:
        return self._history

    def start_monitoring(self) -> None:
        """Inicia o monitoramento de recursos."""
        if self._is_monitoring:
            return

        logger.info("Iniciando monitoramento de recursos")
        self._is_monitoring = True
        self._find_glassfish_process()
        self._timer.start(self._interval)

    def stop_monitoring(self) -> None:
        """Para o monitoramento de recursos."""
        if not self._is_monitoring:
            return

        logger.info("Parando monitoramento de recursos")
        self._is_monitoring = False
        self._timer.stop()

    def clear_history(self) -> None:
        """Limpa o histórico de métricas."""
        self._history.clear()
        self.history_updated.emit()

    def _find_glassfish_process(self) -> None:
        """Encontra o processo do GlassFish."""
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline and any("glassfish" in str(c).lower() for c in cmdline):
                        self._current_pid = proc.info["pid"]
                        logger.debug(f"Processo GlassFish encontrado: PID {self._current_pid}")
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            self._current_pid = None
            logger.debug("Processo GlassFish não encontrado")
        except Exception as e:
            logger.error(f"Erro ao buscar processo GlassFish: {e}")
            self._current_pid = None

    @Slot()
    def _collect_metrics(self) -> None:
        """Coleta métricas do sistema."""
        try:
            if self._gf_service.current_status != ServerStatus.RUNNING:
                return

            if self._current_pid is None:
                self._find_glassfish_process()

            metrics = ResourceMetrics()

            if self._current_pid:
                try:
                    proc = psutil.Process(self._current_pid)

                    if not proc.is_running():
                        self._current_pid = None
                        self._find_glassfish_process()
                        return

                    metrics.cpu_percent = proc.cpu_percent(interval=0.1)
                    mem_info = proc.memory_info()
                    metrics.memory_mb = mem_info.rss / (1024 * 1024)
                    metrics.threads = proc.num_threads()

                    try:
                        metrics.open_files = len(proc.open_files())
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        metrics.open_files = 0

                    try:
                        metrics.connections = len(proc.connections())
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        metrics.connections = 0

                    mem_percent = proc.memory_percent()
                    metrics.memory_percent = mem_percent

                except psutil.NoSuchProcess:
                    logger.debug("Processo GlassFish não encontrado, tentando novamente...")
                    self._current_pid = None
                    self._find_glassfish_process()
                except psutil.AccessDenied:
                    logger.warning("Acesso negado ao processo GlassFish")
            else:
                cpu_total = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                metrics.cpu_percent = cpu_total
                metrics.memory_percent = mem.percent
                metrics.memory_mb = mem.used / (1024 * 1024)

            self._history.add(metrics)
            self.metrics_updated.emit(metrics)
            self.history_updated.emit()

        except Exception as e:
            logger.error(f"Erro ao coletar métricas: {e}")
            self.error_occurred.emit(str(e))

    def get_current_metrics(self) -> ResourceMetrics:
        """Retorna as métricas atuais."""
        if not self._history.cpu:
            return ResourceMetrics()
        return ResourceMetrics(
            cpu_percent=self._history.cpu[-1] if self._history.cpu else 0.0,
            memory_percent=self._history.memory[-1] if self._history.memory else 0.0,
            memory_mb=self._history.memory_mb[-1] if self._history.memory_mb else 0.0,
            threads=self._history.threads[-1] if self._history.threads else 0,
        )
