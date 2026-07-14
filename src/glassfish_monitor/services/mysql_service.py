"""Serviço de gerenciamento do MySQL."""

import enum
import subprocess
from dataclasses import dataclass
from typing import Callable

from loguru import logger
from PySide6.QtCore import QObject, QThread, Signal, Slot

from glassfish_monitor.services.process_manager import CommandResult, ProcessManager


class MySQLStatus(enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class MySQLInfo:
    name: str = "MySQL"
    version: str = ""
    port: int = 3306
    status: MySQLStatus = MySQLStatus.UNKNOWN


class MySQLStatusWorker(QObject):
    finished = Signal(MySQLInfo)
    error = Signal(str)

    def __init__(self, pm: ProcessManager) -> None:
        super().__init__()
        self._pm = pm

    @Slot()
    def run(self) -> None:
        info = MySQLInfo()

        result = self._pm.run_command(["sc", "query", "MySQL"], timeout=10)
        if result.success and "RUNNING" in result.stdout.upper():
            info.status = MySQLStatus.RUNNING
        elif result.success and "STOPPED" in result.stdout.upper():
            info.status = MySQLStatus.STOPPED
        else:
            result2 = self._pm.run_command(["sc", "query", "MySQL80"], timeout=10)
            if result2.success and "RUNNING" in result2.stdout.upper():
                info.status = MySQLStatus.RUNNING
                info.name = "MySQL80"
            elif result2.success and "STOPPED" in result2.stdout.upper():
                info.status = MySQLStatus.STOPPED
                info.name = "MySQL80"
            else:
                result3 = self._pm.run_command(["sc", "query", "MariaDB"], timeout=10)
                if result3.success and "RUNNING" in result3.stdout.upper():
                    info.status = MySQLStatus.RUNNING
                    info.name = "MariaDB"
                elif result3.success and "STOPPED" in result3.stdout.upper():
                    info.status = MySQLStatus.STOPPED
                    info.name = "MariaDB"
                else:
                    info.status = MySQLStatus.UNKNOWN

        ver_result = self._pm.run_command(
            ["mysql", "--version"], timeout=5
        )
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
        self._pm = ProcessManager()
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
            result = self._pm.run_command(["sc", "query", name], timeout=5)
            if result.success and ("RUNNING" in result.stdout.upper() or "STOPPED" in result.stdout.upper()):
                self._service_name = name
                return name
        return self.SERVICE_NAMES[0]

    def check_status_async(self) -> None:
        if self._worker_thread and self._worker_thread.isRunning():
            return

        self._worker_thread = QThread()
        worker = MySQLStatusWorker(self._pm)
        worker.moveToThread(self._worker_thread)
        worker.finished.connect(self._on_status_received)
        worker.error.connect(self._on_status_error)
        self._worker_thread.started.connect(worker.run)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.start()

    def _on_status_received(self, info: MySQLInfo) -> None:
        old = self._current_status
        self._current_status = info.status
        self._service_name = info.name
        if old != info.status:
            self.status_changed.emit(info.status)
        self.info_loaded.emit(info)
        if self._worker_thread:
            self._worker_thread.quit()

    def _on_status_error(self, msg: str) -> None:
        self._current_status = MySQLStatus.ERROR
        self.status_changed.emit(MySQLStatus.ERROR)
        self.error_occurred.emit(msg)
        if self._worker_thread:
            self._worker_thread.quit()

    def start(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        svc = self._find_service_name()

        def _on_complete(result: CommandResult) -> None:
            if result.success:
                self._current_status = MySQLStatus.RUNNING
                self.status_changed.emit(MySQLStatus.RUNNING)
            else:
                self.error_occurred.emit(result.stderr)
            if callback:
                callback(result)
            self.command_executed.emit("start", result.success)

        return self._pm.run_command_async(
            ["net", "start", svc],
            callback=_on_complete,
            output_callback=lambda msg: logger.info(msg),
            command_id="mysql_start",
        )

    def stop(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        svc = self._find_service_name()

        def _on_complete(result: CommandResult) -> None:
            if result.success:
                self._current_status = MySQLStatus.STOPPED
                self.status_changed.emit(MySQLStatus.STOPPED)
            else:
                self.error_occurred.emit(result.stderr)
            if callback:
                callback(result)
            self.command_executed.emit("stop", result.success)

        return self._pm.run_command_async(
            ["net", "stop", svc],
            callback=_on_complete,
            output_callback=lambda msg: logger.info(msg),
            command_id="mysql_stop",
        )

    def restart(self, callback: Callable[[CommandResult], None] | None = None) -> str:
        def _after_stop(result: CommandResult) -> None:
            if result.success:
                self.start(callback)
            else:
                if callback:
                    callback(result)

        return self.stop(callback=_after_stop)
