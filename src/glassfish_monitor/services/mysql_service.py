"""Serviço de gerenciamento do MySQL."""

import subprocess
import enum
from dataclasses import dataclass
from typing import Callable

from loguru import logger
from PySide6.QtCore import QObject, QThread, Signal, Slot


class MySQLStatus(enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    ERROR = "error"


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
class MySQLInfo:
    name: str = "MySQL"
    version: str = ""
    port: int = 3306
    status: MySQLStatus = MySQLStatus.UNKNOWN


def _run_system_command(args: list[str], timeout: int = 10) -> CommandResult:
    cmd_str = " ".join(args)
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
        return CommandResult(command=cmd_str, returncode=-2, stdout="", stderr="Comando não encontrado")
    except subprocess.TimeoutExpired:
        return CommandResult(command=cmd_str, returncode=-1, stdout="", stderr="Timeout")
    except Exception as e:
        return CommandResult(command=cmd_str, returncode=-3, stdout="", stderr=str(e))


class MySQLStatusWorker(QObject):
    finished = Signal(MySQLInfo)
    error = Signal(str)

    @Slot()
    def run(self) -> None:
        info = MySQLInfo()

        for name in ["MySQL", "MySQL80", "MariaDB"]:
            result = _run_system_command(["sc", "query", name], timeout=10)
            if result.returncode == 0:
                info.name = name
                if "RUNNING" in result.stdout.upper():
                    info.status = MySQLStatus.RUNNING
                elif "STOPPED" in result.stdout.upper():
                    info.status = MySQLStatus.STOPPED
                break

        ver_result = _run_system_command(["mysql", "--version"], timeout=5)
        if ver_result.success:
            info.version = ver_result.stdout.strip()

        self.finished.emit(info)


class MySQLService(QObject):
    status_changed = Signal(MySQLStatus)
    command_executed = Signal(str, bool)
    error_occurred = Signal(str)
    info_loaded = Signal(MySQLInfo)

    SERVICE_NAMES = ["MySQL", "MySQL80", "MariaDB"]

    def __init__(self) -> None:
        super().__init__()
        self._current_status = MySQLStatus.UNKNOWN
        self._service_name: str | None = None
        self._worker_thread: QThread | None = None

    @property
    def current_status(self) -> MySQLStatus:
        return self._current_status

    def _find_service_name(self) -> str:
        if self._service_name:
            return self._service_name
        for name in self.SERVICE_NAMES:
            result = _run_system_command(["sc", "query", name], timeout=5)
            if result.returncode == 0:
                self._service_name = name
                return name
        return self.SERVICE_NAMES[0]

    def check_status_async(self) -> None:
        if self._worker_thread is not None:
            try:
                if self._worker_thread.isRunning():
                    return
            except RuntimeError:
                pass
            self._worker_thread = None

        self._worker_thread = QThread()
        worker = MySQLStatusWorker()
        worker.moveToThread(self._worker_thread)
        worker.finished.connect(self._on_status_received)
        worker.error.connect(self._on_status_error)
        self._worker_thread.started.connect(worker.run)
        self._worker_thread.finished.connect(self._worker_thread.quit)
        self._worker_thread.start()

    def _on_status_received(self, info: MySQLInfo) -> None:
        old = self._current_status
        self._current_status = info.status
        self._service_name = info.name
        if old != info.status:
            self.status_changed.emit(info.status)
        self.info_loaded.emit(info)

    def _on_status_error(self, msg: str) -> None:
        self._current_status = MySQLStatus.ERROR
        self.status_changed.emit(MySQLStatus.ERROR)
        self.error_occurred.emit(msg)

    def _run_net_command(self, action: str, callback: Callable[[CommandResult], None] | None = None) -> str:
        svc = self._find_service_name()
        args = ["net", action, svc]

        def _on_complete(result: CommandResult) -> None:
            if result.success:
                self._current_status = MySQLStatus.RUNNING if action == "start" else MySQLStatus.STOPPED
                self.status_changed.emit(self._current_status)
            else:
                self.error_occurred.emit(result.stderr)
            if callback:
                callback(result)
            self.command_executed.emit(action, result.success)

        thread = QThread()
        worker = _SystemCommandWorker(args)
        worker.moveToThread(thread)
        worker.finished.connect(_on_complete)
        thread.started.connect(worker.run)
        thread.finished.connect(thread.quit)
        thread.start()
        return action

    def start(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        return self._run_net_command("start", callback)

    def stop(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        return self._run_net_command("stop", callback)

    def restart(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        def _after_stop(result: CommandResult) -> None:
            if result.success:
                self.start(callback)
            elif callback:
                callback(result)
        return self._run_net_command("stop", _after_stop)


class _SystemCommandWorker(QObject):
    finished = Signal(CommandResult)

    def __init__(self, args: list[str]) -> None:
        super().__init__()
        self._args = args

    @Slot()
    def run(self) -> None:
        result = _run_system_command(self._args, timeout=30)
        self.finished.emit(result)
