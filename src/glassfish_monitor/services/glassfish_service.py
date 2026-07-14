"""Serviço principal de interação com o GlassFish Server."""

import enum
import subprocess
import threading
from dataclasses import dataclass

from loguru import logger
from PySide6.QtCore import Qt, QObject, Signal

from glassfish_monitor.config import GlassFishConfig


class ServerStatus(enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    RESTART_REQUIRED = "restart_required"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class DomainInfo:
    name: str
    status: ServerStatus
    admin_port: int = GlassFishConfig.ADMIN_PORT
    http_port: int = GlassFishConfig.HTTP_PORT


@dataclass
class GlassFishVersion:
    product_name: str = ""
    version: str = ""
    build_id: str = ""


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


@dataclass
class DeployedApp:
    name: str
    context_root: str = ""
    status: str = ""


def _run_subprocess(args: list[str], timeout: int | None = None) -> CommandResult:
    cmd_str = " ".join(args)
    timeout = timeout or GlassFishConfig.COMMAND_TIMEOUT

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
            encoding="cp1252",
            errors="replace",
        )
        return CommandResult(
            command=cmd_str,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except FileNotFoundError:
        return CommandResult(command=cmd_str, returncode=-2, stdout="", stderr=f"Não encontrado: {cmd_str}")
    except subprocess.TimeoutExpired:
        return CommandResult(command=cmd_str, returncode=-1, stdout="", stderr="Timeout")
    except Exception as e:
        return CommandResult(command=cmd_str, returncode=-3, stdout="", stderr=str(e))


def _run_asadmin(args: list[str], timeout: int | None = None) -> CommandResult:
    asadmin_path = str(GlassFishConfig.get_asadmin_path())
    return _run_subprocess([asadmin_path] + args, timeout)


class GlassFishService(QObject):
    status_changed = Signal(ServerStatus)
    command_executed = Signal(str, bool)
    error_occurred = Signal(str)

    _result_ready = Signal(object)

    def __init__(self, domain_name: str | None = None) -> None:
        super().__init__()
        self._domain_name = domain_name or GlassFishConfig.DOMAIN_NAME
        self._current_status = ServerStatus.UNKNOWN
        self._pending_callbacks: list = []
        self._result_ready.connect(self._handle_result, Qt.ConnectionType.QueuedConnection)

    @property
    def domain_name(self) -> str:
        return self._domain_name

    @property
    def current_status(self) -> ServerStatus:
        return self._current_status

    def validate_installation(self) -> tuple[bool, str]:
        return GlassFishConfig.validate_glassfish_installation()

    def _run_async(self, func, callback) -> None:
        self._pending_callbacks.append(callback)

        def _worker() -> None:
            result = func()
            self._result_ready.emit(result)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _handle_result(self, result) -> None:
        callback = self._pending_callbacks.pop(0)
        callback(result)

    def check_status_async(self) -> None:
        def _do():
            return _run_asadmin(["list-domains", "--domaindir", str(GlassFishConfig.get_domains_dir())])

        def _on_result(result: CommandResult) -> None:
            if result.success:
                info = self._parse_list_domains(result.stdout)
                self._current_status = info.status
            else:
                self._current_status = ServerStatus.ERROR
            logger.info(f"Status: {self._current_status.value}")
            self.status_changed.emit(self._current_status)

        self._run_async(_do, _on_result)

    def start_domain(self, callback=None) -> None:
        logger.info(f"Iniciando domínio: {self._domain_name}")

        def _do():
            return _run_asadmin(["start-domain", self._domain_name], timeout=GlassFishConfig.STARTUP_TIMEOUT)

        def _on_result(result: CommandResult) -> None:
            if result.success:
                self._current_status = ServerStatus.RUNNING
                self.status_changed.emit(ServerStatus.RUNNING)
            else:
                self.error_occurred.emit(result.stderr or "Erro ao iniciar domínio")
            if callback:
                callback(result)
            self.command_executed.emit("start-domain", result.success)

        self._run_async(_do, _on_result)

    def stop_domain(self, callback=None) -> None:
        logger.info(f"Parando domínio: {self._domain_name}")

        def _do():
            return _run_asadmin(["stop-domain", self._domain_name])

        def _on_result(result: CommandResult) -> None:
            if result.success:
                self._current_status = ServerStatus.STOPPED
                self.status_changed.emit(ServerStatus.STOPPED)
            else:
                self.error_occurred.emit(result.stderr or "Erro ao parar domínio")
            if callback:
                callback(result)
            self.command_executed.emit("stop-domain", result.success)

        self._run_async(_do, _on_result)

    def restart_domain(self, callback=None) -> None:
        logger.info(f"Reiniciando domínio: {self._domain_name}")

        def _do():
            return _run_asadmin(["restart-domain", self._domain_name], timeout=GlassFishConfig.STARTUP_TIMEOUT)

        def _on_result(result: CommandResult) -> None:
            if result.success:
                self._current_status = ServerStatus.RUNNING
                self.status_changed.emit(ServerStatus.RUNNING)
            else:
                self.error_occurred.emit(result.stderr or "Erro ao reiniciar domínio")
            if callback:
                callback(result)
            self.command_executed.emit("restart-domain", result.success)

        self._run_async(_do, _on_result)

    def list_deployed_apps(self) -> list[DeployedApp]:
        result = _run_asadmin(["list-applications", "--long"])
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
                context_root = parts[1] if len(parts) >= 2 else ""
                status_str = "disabled" if "disabled" in line.lower() else "enabled"
                apps.append(DeployedApp(name=name, context_root=context_root, status=status_str))
        return apps

    def get_version(self) -> GlassFishVersion | None:
        result = _run_asadmin(["version", "--verbose=false"])
        if not result.success:
            return None
        vi = GlassFishVersion()
        for line in result.stdout.splitlines():
            if "GlassFish" in line:
                vi.product_name = line.strip()
            elif "Version:" in line:
                vi.version = line.split(":", 1)[1].strip()
        return vi

    def _parse_list_domains(self, output: str) -> DomainInfo:
        for line in output.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == self._domain_name:
                status_str = parts[1].lower()
                if status_str == "running":
                    status = (
                        ServerStatus.RESTART_REQUIRED
                        if "restart required" in line.lower()
                        else ServerStatus.RUNNING
                    )
                elif status_str == "notrunning":
                    status = ServerStatus.STOPPED
                else:
                    status = ServerStatus.UNKNOWN
                return DomainInfo(name=self._domain_name, status=status)
        return DomainInfo(name=self._domain_name, status=ServerStatus.UNKNOWN)
