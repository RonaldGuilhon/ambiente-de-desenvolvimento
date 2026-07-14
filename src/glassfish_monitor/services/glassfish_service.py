"""Serviço principal de interação com o GlassFish Server."""

import enum
import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, QThread, Signal, Slot

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
    pid: int | None = None


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


class _CommandWorker(QObject):
    """Worker que executa um comando asadmin em QThread."""

    finished = Signal(CommandResult)
    output = Signal(str)

    def __init__(self, args: list[str]) -> None:
        super().__init__()
        self._args = args

    @Slot()
    def run(self) -> None:
        import subprocess

        asadmin_path = str(GlassFishConfig.get_asadmin_path())
        cmd = [asadmin_path] + self._args
        cmd_str = " ".join(cmd)

        logger.debug(f"Executando comando: {cmd_str}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding="cp1252",
                errors="replace",
            )

            stdout_lines: list[str] = []
            stderr_lines: list[str] = []

            if process.stdout:
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        stdout_lines.append(line)
                        self.output.emit(line)

            if process.stderr:
                for line in process.stderr:
                    line = line.strip()
                    if line:
                        stderr_lines.append(line)
                        self.output.emit(f"[ERRO] {line}")

            process.wait(timeout=GlassFishConfig.COMMAND_TIMEOUT)

            result = CommandResult(
                command=cmd_str,
                returncode=process.returncode or 0,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
            )
            logger.debug(f"Comando finalizado com código: {result.returncode}")

        except subprocess.TimeoutExpired:
            logger.error(f"Comando expirou: {cmd_str}")
            result = CommandResult(command=cmd_str, returncode=-1, stdout="", stderr="Timeout")
        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")
            result = CommandResult(command=cmd_str, returncode=-3, stdout="", stderr=str(e))

        self.finished.emit(result)


class _SyncCommandWorker(QObject):
    """Worker para comandos síncronos em QThread."""

    finished = Signal(object)

    def __init__(self, func, *args, **kwargs) -> None:
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    @Slot()
    def run(self) -> None:
        result = self._func(*self._args, **self._kwargs)
        self.finished.emit(result)


class GlassFishService(QObject):
    status_changed = Signal(ServerStatus)
    command_executed = Signal(str, bool)
    error_occurred = Signal(str)
    log_message = Signal(str)

    def __init__(self, domain_name: str | None = None) -> None:
        super().__init__()
        self._domain_name = domain_name or GlassFishConfig.DOMAIN_NAME
        self._current_status = ServerStatus.UNKNOWN
        self._active_threads: list[QThread] = []

    @property
    def domain_name(self) -> str:
        return self._domain_name

    @property
    def current_status(self) -> ServerStatus:
        return self._current_status

    def validate_installation(self) -> tuple[bool, str]:
        return GlassFishConfig.validate_glassfish_installation()

    def _run_async(self, args: list[str], callback=None) -> None:
        """Executa um comando asadmin em background com QThread."""
        thread = QThread()
        worker = _CommandWorker(args)
        worker.moveToThread(thread)

        def _on_finished(result: CommandResult) -> None:
            if callback:
                callback(result)
            thread.quit()

        worker.finished.connect(_on_finished)
        worker.output.connect(self.log_message)
        thread.started.connect(worker.run)
        thread.finished.connect(lambda: self._cleanup_thread(thread))

        self._active_threads.append(thread)
        thread.start()

    def _cleanup_thread(self, thread: QThread) -> None:
        if thread in self._active_threads:
            self._active_threads.remove(thread)

    def check_status_async(self) -> None:
        def _on_result(result: CommandResult) -> None:
            old = self._current_status
            if result.success:
                info = self._parse_list_domains(result.stdout, self._domain_name)
                self._current_status = info.status
            else:
                self._current_status = ServerStatus.ERROR

            if old != self._current_status:
                logger.info(f"Status: {old.value} -> {self._current_status.value}")
                self.status_changed.emit(self._current_status)

        self._run_async(
            ["list-domains", "--domaindir", str(GlassFishConfig.get_domains_dir())],
            callback=_on_result,
        )

    def _parse_list_domains(self, output: str, domain_name: str) -> DomainInfo:
        for line in output.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == domain_name:
                status_str = parts[1].lower()
                if status_str == "running":
                    status = ServerStatus.RESTART_REQUIRED if "restart required" in line.lower() else ServerStatus.RUNNING
                elif status_str == "notrunning":
                    status = ServerStatus.STOPPED
                else:
                    status = ServerStatus.UNKNOWN
                return DomainInfo(name=domain_name, status=status)
        return DomainInfo(name=domain_name, status=ServerStatus.UNKNOWN)

    def start_domain(self, callback=None) -> None:
        logger.info(f"Iniciando domínio: {self._domain_name}")

        def _on_result(result: CommandResult) -> None:
            if result.success:
                self._current_status = ServerStatus.RUNNING
                self.status_changed.emit(ServerStatus.RUNNING)
            else:
                self.error_occurred.emit(result.stderr or "Erro ao iniciar domínio")
            if callback:
                callback(result)
            self.command_executed.emit("start-domain", result.success)

        self._run_async(["start-domain", self._domain_name], callback=_on_result)

    def stop_domain(self, callback=None) -> None:
        logger.info(f"Parando domínio: {self._domain_name}")

        def _on_result(result: CommandResult) -> None:
            if result.success:
                self._current_status = ServerStatus.STOPPED
                self.status_changed.emit(ServerStatus.STOPPED)
            else:
                self.error_occurred.emit(result.stderr or "Erro ao parar domínio")
            if callback:
                callback(result)
            self.command_executed.emit("stop-domain", result.success)

        self._run_async(["stop-domain", self._domain_name], callback=_on_result)

    def restart_domain(self, callback=None) -> None:
        logger.info(f"Reiniciando domínio: {self._domain_name}")

        def _on_result(result: CommandResult) -> None:
            if result.success:
                self._current_status = ServerStatus.RUNNING
                self.status_changed.emit(ServerStatus.RUNNING)
            else:
                self.error_occurred.emit(result.stderr or "Erro ao reiniciar domínio")
            if callback:
                callback(result)
            self.command_executed.emit("restart-domain", result.success)

        self._run_async(["restart-domain", self._domain_name], callback=_on_result)

    def list_domains(self) -> list[DomainInfo]:
        result = self._run_sync(
            ["list-domains", "--domaindir", str(GlassFishConfig.get_domains_dir())]
        )
        if not result.success:
            return []
        return self._parse_domains_output(result.stdout)

    def _parse_domains_output(self, output: str) -> list[DomainInfo]:
        domains: list[DomainInfo] = []
        for line in output.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                status_str = parts[1].lower()
                if status_str == "running":
                    status = ServerStatus.RESTART_REQUIRED if "restart required" in line.lower() else ServerStatus.RUNNING
                elif status_str == "notrunning":
                    status = ServerStatus.STOPPED
                else:
                    status = ServerStatus.UNKNOWN
                domains.append(DomainInfo(name=name, status=status))
        return domains

    def get_version(self) -> GlassFishVersion | None:
        result = self._run_sync(["version", "--verbose=false"])
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

    def list_deployed_apps(self) -> list:
        from glassfish_monitor.services.glassfish_service import DeployedApp

        result = self._run_sync(["list-applications", "--long"])
        if not result.success:
            return []
        apps = []
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

    def _run_sync(self, args: list[str]) -> CommandResult:
        """Executa comando síncrono."""
        import subprocess

        asadmin_path = str(GlassFishConfig.get_asadmin_path())
        cmd = [asadmin_path] + args
        cmd_str = " ".join(cmd)
        logger.debug(f"Executando comando: {cmd_str}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=GlassFishConfig.COMMAND_TIMEOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding="cp1252",
                errors="replace",
            )
            logger.debug(f"Comando finalizado com código: {result.returncode}")
            return CommandResult(
                command=cmd_str,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except FileNotFoundError:
            return CommandResult(command=cmd_str, returncode=-2, stdout="", stderr=f"asadmin não encontrado: {asadmin_path}")
        except subprocess.TimeoutExpired:
            return CommandResult(command=cmd_str, returncode=-1, stdout="", stderr="Timeout")
        except Exception as e:
            return CommandResult(command=cmd_str, returncode=-3, stdout="", stderr=str(e))


@dataclass
class DeployedApp:
    name: str
    context_root: str = ""
    status: str = ""
