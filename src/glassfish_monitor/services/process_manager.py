"""Gerenciamento de processos para comandos GlassFish."""

import subprocess
import threading
from dataclasses import dataclass, field
from typing import Callable

from loguru import logger

from glassfish_monitor.config import GlassFishConfig


@dataclass
class CommandResult:
    """Resultado de uma execução de comando."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    success: bool = field(init=False)

    def __post_init__(self) -> None:
        self.success = self.returncode == 0


@dataclass
class AsyncCommand:
    """Comando assíncrono em execução."""

    process: subprocess.Popen[str] | None = None
    thread: threading.Thread | None = None
    cancelled: bool = False


class ProcessManager:
    """Gerencia execução de comandos do asadmin."""

    def __init__(self) -> None:
        self._active_commands: dict[str, AsyncCommand] = {}

    def run_command(
        self,
        args: list[str],
        timeout: int | None = None,
        capture_output: bool = True,
    ) -> CommandResult:
        """Executa um comando de forma síncrona."""
        asadmin_path = str(GlassFishConfig.get_asadmin_path())
        cmd = [asadmin_path] + args
        cmd_str = " ".join(cmd)

        logger.debug(f"Executando comando: {cmd_str}")

        timeout = timeout or GlassFishConfig.COMMAND_TIMEOUT

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
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
        except subprocess.TimeoutExpired:
            logger.error(f"Comando expirou o tempo limite: {cmd_str}")
            return CommandResult(
                command=cmd_str,
                returncode=-1,
                stdout="",
                stderr=f"Comando expirou o tempo limite ({timeout}s)",
            )
        except FileNotFoundError:
            logger.error(f"asadmin.bat não encontrado em: {asadmin_path}")
            return CommandResult(
                command=cmd_str,
                returncode=-2,
                stdout="",
                stderr=f"asadmin.bat não encontrado: {asadmin_path}",
            )
        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")
            return CommandResult(
                command=cmd_str,
                returncode=-3,
                stdout="",
                stderr=str(e),
            )

    def run_command_async(
        self,
        args: list[str],
        callback: Callable[[CommandResult], None] | None = None,
        output_callback: Callable[[str], None] | None = None,
        command_id: str | None = None,
    ) -> str:
        """Executa um comando de forma assíncrona com callbacks."""
        asadmin_path = str(GlassFishConfig.get_asadmin_path())
        cmd = [asadmin_path] + args
        cmd_str = " ".join(cmd)
        cmd_id = command_id or f"cmd_{id(args)}"

        logger.debug(f"Executando comando assíncrono: {cmd_str}")

        def _run() -> None:
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

                if cmd_id in self._active_commands:
                    self._active_commands[cmd_id].process = process

                stdout_lines: list[str] = []
                stderr_lines: list[str] = []

                if process.stdout:
                    for line in process.stdout:
                        if self._active_commands.get(cmd_id, AsyncCommand()).cancelled:
                            process.terminate()
                            break
                        line = line.strip()
                        if line:
                            stdout_lines.append(line)
                            if output_callback:
                                output_callback(line)

                if process.stderr:
                    for line in process.stderr:
                        line = line.strip()
                        if line:
                            stderr_lines.append(line)
                            if output_callback:
                                output_callback(f"[ERRO] {line}")

                process.wait(timeout=GlassFishConfig.COMMAND_TIMEOUT)
                returncode = process.returncode or 0

                result = CommandResult(
                    command=cmd_str,
                    returncode=returncode,
                    stdout="\n".join(stdout_lines),
                    stderr="\n".join(stderr_lines),
                )

                if callback:
                    callback(result)

            except subprocess.TimeoutExpired:
                logger.error(f"Comando assíncrono expirou: {cmd_str}")
                if callback:
                    callback(
                        CommandResult(
                            command=cmd_str,
                            returncode=-1,
                            stdout="",
                            stderr="Comando expirou o tempo limite",
                        )
                    )
            except Exception as e:
                logger.error(f"Erro no comando assíncrono: {e}")
                if callback:
                    callback(
                        CommandResult(
                            command=cmd_str,
                            returncode=-3,
                            stdout="",
                            stderr=str(e),
                        )
                    )
            finally:
                if cmd_id in self._active_commands:
                    del self._active_commands[cmd_id]

        async_cmd = AsyncCommand()
        self._active_commands[cmd_id] = async_cmd

        thread = threading.Thread(target=_run, daemon=True, name=f"asadmin-{cmd_id}")
        async_cmd.thread = thread
        thread.start()

        return cmd_id

    def cancel_command(self, command_id: str) -> bool:
        """Cancela um comando assíncrono em execução."""
        if command_id in self._active_commands:
            self._active_commands[command_id].cancelled = True
            process = self._active_commands[command_id].process
            if process and process.poll() is None:
                process.terminate()
            logger.debug(f"Comando cancelado: {command_id}")
            return True
        return False

    def is_command_running(self, command_id: str) -> bool:
        """Verifica se um comando está em execução."""
        if command_id not in self._active_commands:
            return False
        thread = self._active_commands[command_id].thread
        return thread is not None and thread.is_alive()

    def cancel_all(self) -> None:
        """Cancela todos os comandos em execução."""
        for cmd_id in list(self._active_commands.keys()):
            self.cancel_command(cmd_id)
