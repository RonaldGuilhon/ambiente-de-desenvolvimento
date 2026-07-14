"""Serviço principal de interação com o GlassFish Server."""

import enum
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from loguru import logger
from PySide6.QtCore import QObject, QThread, Signal, Slot

from glassfish_monitor.config import GlassFishConfig
from glassfish_monitor.services.process_manager import CommandResult, ProcessManager


class ServerStatus(enum.Enum):
    """Status do servidor GlassFish."""

    RUNNING = "running"
    STOPPED = "stopped"
    RESTART_REQUIRED = "restart_required"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class DomainInfo:
    """Informações de um domínio GlassFish."""

    name: str
    status: ServerStatus
    admin_port: int = GlassFishConfig.ADMIN_PORT
    http_port: int = GlassFishConfig.HTTP_PORT
    pid: int | None = None


@dataclass
class GlassFishVersion:
    """Informações de versão do GlassFish."""

    product_name: str = ""
    version: str = ""
    build_id: str = ""


class StatusWorker(QObject):
    """Worker para verificar status em background."""

    finished = Signal(DomainInfo)
    error = Signal(str)

    def __init__(self, process_manager: ProcessManager, domain_name: str) -> None:
        super().__init__()
        self._pm = process_manager
        self._domain_name = domain_name

    @Slot()
    def run(self) -> None:
        result = self._pm.run_command(["list-domains", "--domaindir", str(GlassFishConfig.get_domains_dir())])
        if not result.success:
            self.error.emit(result.stderr or "Falha ao listar domínios")
            return

        info = self._parse_list_domains(result.stdout, self._domain_name)
        self.finished.emit(info)

    def _parse_list_domains(self, output: str, domain_name: str) -> DomainInfo:
        for line in output.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == domain_name:
                status_str = parts[1].lower()
                if status_str == "running":
                    if "restart required" in line.lower():
                        status = ServerStatus.RESTART_REQUIRED
                    else:
                        status = ServerStatus.RUNNING
                elif status_str == "notrunning":
                    status = ServerStatus.STOPPED
                else:
                    status = ServerStatus.UNKNOWN
                return DomainInfo(name=domain_name, status=status)
        return DomainInfo(name=domain_name, status=ServerStatus.UNKNOWN)


@dataclass
class DeployedApp:
    """Aplicação deployada no GlassFish."""

    name: str
    context_root: str = ""
    status: str = ""


class GlassFishService(QObject):
    """Serviço principal de interação com o GlassFish."""

    status_changed = Signal(ServerStatus)
    command_executed = Signal(str, bool)
    error_occurred = Signal(str)
    log_message = Signal(str)

    def __init__(self, domain_name: str | None = None) -> None:
        super().__init__()
        self._domain_name = domain_name or GlassFishConfig.DOMAIN_NAME
        self._process_manager = ProcessManager()
        self._current_status = ServerStatus.UNKNOWN
        self._status_check_interval = 5
        self._worker_thread: QThread | None = None
        self._worker: StatusWorker | None = None

    @property
    def domain_name(self) -> str:
        return self._domain_name

    @property
    def current_status(self) -> ServerStatus:
        return self._current_status

    def validate_installation(self) -> tuple[bool, str]:
        """Valida se o GlassFish está instalado."""
        return GlassFishConfig.validate_glassfish_installation()

    def check_status_async(self) -> None:
        """Verifica o status do servidor de forma assíncrona."""
        if self._worker_thread and self._worker_thread.isRunning():
            return

        self._worker_thread = QThread()
        self._worker = StatusWorker(self._process_manager, self._domain_name)
        self._worker.moveToThread(self._worker_thread)

        self._worker.finished.connect(self._on_status_received)
        self._worker.error.connect(self._on_status_error)
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        self._worker_thread.start()

    def _on_status_received(self, info: DomainInfo) -> None:
        """Callback quando status é recebido."""
        old_status = self._current_status
        self._current_status = info.status

        if old_status != info.status:
            logger.info(f"Status alterado: {old_status.value} -> {info.status.value}")
            self.status_changed.emit(info.status)

        if self._worker_thread:
            self._worker_thread.quit()

    def _on_status_error(self, error_msg: str) -> None:
        """Callback quando ocorre erro ao verificar status."""
        logger.error(f"Erro ao verificar status: {error_msg}")
        self._current_status = ServerStatus.ERROR
        self.status_changed.emit(ServerStatus.ERROR)
        self.error_occurred.emit(error_msg)

        if self._worker_thread:
            self._worker_thread.quit()

    def start_domain(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        """Inicia o domínio do GlassFish."""
        logger.info(f"Iniciando domínio: {self._domain_name}")
        self.log_message.emit(f"Iniciando domínio {self._domain_name}...")

        def _on_complete(result: CommandResult) -> None:
            if result.success:
                self.log_message.emit(f"Domínio {self._domain_name} iniciado com sucesso")
                self._current_status = ServerStatus.RUNNING
                self.status_changed.emit(ServerStatus.RUNNING)
            else:
                self.log_message.emit(f"Erro ao iniciar domínio: {result.stderr}")
                self.error_occurred.emit(result.stderr)

            if callback:
                callback(result)

            self.command_executed.emit("start-domain", result.success)

        return self._process_manager.run_command_async(
            ["start-domain", self._domain_name],
            callback=_on_complete,
            output_callback=lambda msg: self.log_message.emit(msg),
            command_id="start_domain",
        )

    def stop_domain(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        """Para o domínio do GlassFish."""
        logger.info(f"Parando domínio: {self._domain_name}")
        self.log_message.emit(f"Parando domínio {self._domain_name}...")

        def _on_complete(result: CommandResult) -> None:
            if result.success:
                self.log_message.emit(f"Domínio {self._domain_name} parado com sucesso")
                self._current_status = ServerStatus.STOPPED
                self.status_changed.emit(ServerStatus.STOPPED)
            else:
                self.log_message.emit(f"Erro ao parar domínio: {result.stderr}")
                self.error_occurred.emit(result.stderr)

            if callback:
                callback(result)

            self.command_executed.emit("stop-domain", result.success)

        return self._process_manager.run_command_async(
            ["stop-domain", self._domain_name],
            callback=_on_complete,
            output_callback=lambda msg: self.log_message.emit(msg),
            command_id="stop_domain",
        )

    def restart_domain(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        """Reinicia o domínio do GlassFish."""
        logger.info(f"Reiniciando domínio: {self._domain_name}")
        self.log_message.emit(f"Reiniciando domínio {self._domain_name}...")

        def _on_complete(result: CommandResult) -> None:
            if result.success:
                self.log_message.emit(f"Domínio {self._domain_name} reiniciado com sucesso")
                self._current_status = ServerStatus.RUNNING
                self.status_changed.emit(ServerStatus.RUNNING)
            else:
                self.log_message.emit(f"Erro ao reiniciar domínio: {result.stderr}")
                self.error_occurred.emit(result.stderr)

            if callback:
                callback(result)

            self.command_executed.emit("restart-domain", result.success)

        return self._process_manager.run_command_async(
            ["restart-domain", self._domain_name],
            callback=_on_complete,
            output_callback=lambda msg: self.log_message.emit(msg),
            command_id="restart_domain",
        )

    def list_domains(self) -> list[DomainInfo]:
        """Lista todos os domínios."""
        result = self._process_manager.run_command(
            ["list-domains", "--domaindir", str(GlassFishConfig.get_domains_dir())]
        )
        if not result.success:
            logger.error(f"Erro ao listar domínios: {result.stderr}")
            return []

        return self._parse_domains_output(result.stdout)

    def _parse_domains_output(self, output: str) -> list[DomainInfo]:
        """Parse a saída do comando list-domains."""
        domains: list[DomainInfo] = []
        for line in output.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                status_str = parts[1].lower()
                if status_str == "running":
                    if "restart required" in line.lower():
                        status = ServerStatus.RESTART_REQUIRED
                    else:
                        status = ServerStatus.RUNNING
                elif status_str == "notrunning":
                    status = ServerStatus.STOPPED
                else:
                    status = ServerStatus.UNKNOWN
                domains.append(DomainInfo(name=name, status=status))
        return domains

    def get_version(self) -> GlassFishVersion | None:
        """Obtém informações de versão do GlassFish."""
        result = self._process_manager.run_command(["version", "--verbose=false"])
        if not result.success:
            return None

        version_info = GlassFishVersion()
        for line in result.stdout.splitlines():
            if "GlassFish" in line:
                version_info.product_name = line.strip()
            elif "Version:" in line:
                version_info.version = line.split(":", 1)[1].strip()
            elif "Build" in line and ":" in line:
                version_info.build_id = line.split(":", 1)[1].strip()

        return version_info

    def is_running(self) -> bool:
        """Verifica se o servidor está rodando."""
        result = self._process_manager.run_command(
            ["list-domains", "--domaindir", str(GlassFishConfig.get_domains_dir())]
        )
        if not result.success:
            return False

        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == self._domain_name:
                return parts[1].lower() == "running"
        return False

    def get_domain_pid(self) -> int | None:
        """Obtém o PID do processo do domínio."""
        result = self._process_manager.run_command(
            ["list-domains", "--long", "--domaindir", str(GlassFishConfig.get_domains_dir())]
        )
        if not result.success:
            return None

        for line in result.stdout.splitlines():
            if "PID" in line or "pid" in line:
                pid_match = re.search(r"(\d+)", line)
                if pid_match:
                    return int(pid_match.group(1))
        return None

    def cancel_operation(self, operation_id: str) -> bool:
        """Cancela uma operação em andamento."""
        return self._process_manager.cancel_command(operation_id)

    def cancel_all_operations(self) -> None:
        """Cancela todas as operações em andamento."""
        self._process_manager.cancel_all()

    def list_deployed_apps(self) -> list[DeployedApp]:
        """Lista aplicações deployadas no GlassFish."""
        result = self._process_manager.run_command(
            ["list-applications", "--long"]
        )
        if not result.success:
            return []

        apps: list[DeployedApp] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line or "Command" in line:
                continue
            parts = line.split()
            if len(parts) >= 1:
                name = parts[0]
                context_root = ""
                status_str = "enabled"
                if len(parts) >= 2:
                    context_root = parts[1]
                if "disabled" in line.lower():
                    status_str = "disabled"
                apps.append(DeployedApp(name=name, context_root=context_root, status=status_str))
        return apps
