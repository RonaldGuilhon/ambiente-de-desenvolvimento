"""Serviço de gerenciamento do PostgreSQL."""

import enum
import subprocess
import threading
from dataclasses import dataclass

from loguru import logger
from PySide6.QtCore import Qt, QObject, Signal


class PostgresStatus(enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class PostgresInfo:
    name: str = "PostgreSQL"
    version: str = ""
    port: int = 5432
    status: PostgresStatus = PostgresStatus.UNKNOWN


def _run_cmd(args: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
            encoding="cp1252", errors="replace",
        )
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -2, "", "Comando não encontrado"
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -3, "", str(e)


class PostgresService(QObject):
    status_changed = Signal(PostgresStatus)
    command_executed = Signal(str, bool)
    error_occurred = Signal(str)
    info_loaded = Signal(PostgresInfo)

    _result_ready = Signal(object)

    SERVICE_NAMES = [
        "postgresql", "postgresql-x64-16", "postgresql-x64-15",
        "postgresql-x64-14", "postgresql-x64-13",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_status = PostgresStatus.UNKNOWN
        self._service_name: str | None = None
        self._pending_callbacks: list = []
        self._result_ready.connect(self._handle_result, Qt.ConnectionType.QueuedConnection)

    @property
    def current_status(self) -> PostgresStatus:
        return self._current_status

    def _find_service_name(self) -> str:
        if self._service_name:
            return self._service_name
        for name in self.SERVICE_NAMES:
            rc, out, _ = _run_cmd(["sc", "query", name], timeout=5)
            if rc == 0:
                self._service_name = name
                return name
        return self.SERVICE_NAMES[0]

    def _run_async(self, func, callback) -> None:
        self._pending_callbacks.append(callback)

        def _worker():
            result = func()
            self._result_ready.emit(result)

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_result(self, result) -> None:
        callback = self._pending_callbacks.pop(0)
        callback(result)

    def check_status_async(self) -> None:
        def _do():
            info = PostgresInfo()
            for name in self.SERVICE_NAMES:
                rc, out, _ = _run_cmd(["sc", "query", name])
                if rc == 0:
                    info.name = name
                    upper = out.upper()
                    if "RUNNING" in upper:
                        info.status = PostgresStatus.RUNNING
                    elif "STOPPED" in upper:
                        info.status = PostgresStatus.STOPPED
                    break

            rc, out, _ = _run_cmd(["psql", "--version"], timeout=5)
            if rc == 0:
                info.version = out.strip()
            return info

        def _on_result(info: PostgresInfo):
            self._current_status = info.status
            self._service_name = info.name
            self.status_changed.emit(info.status)
            self.info_loaded.emit(info)

        self._run_async(_do, _on_result)

    def start(self, callback=None) -> None:
        svc = self._find_service_name()

        def _do():
            return _run_cmd(["net", "start", svc], timeout=30)

        def _on_result(result):
            rc, out, err = result
            if rc == 0:
                self._current_status = PostgresStatus.RUNNING
                self.status_changed.emit(PostgresStatus.RUNNING)
            else:
                self.error_occurred.emit(err)
            if callback:
                callback(result)
            self.command_executed.emit("start", rc == 0)

        self._run_async(_do, _on_result)

    def stop(self, callback=None) -> None:
        svc = self._find_service_name()

        def _do():
            return _run_cmd(["net", "stop", svc], timeout=30)

        def _on_result(result):
            rc, out, err = result
            if rc == 0:
                self._current_status = PostgresStatus.STOPPED
                self.status_changed.emit(PostgresStatus.STOPPED)
            else:
                self.error_occurred.emit(err)
            if callback:
                callback(result)
            self.command_executed.emit("stop", rc == 0)

        self._run_async(_do, _on_result)

    def restart(self, callback=None) -> None:
        def _after_stop(result):
            rc, _, _ = result
            if rc == 0:
                self.start(callback)
            elif callback:
                callback(result)
        self.stop(callback=_after_stop)
