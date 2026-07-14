"""Visualizador de logs do GlassFish."""

import re
from datetime import datetime
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from glassfish_monitor.config import GlassFishConfig
from glassfish_monitor.ui.styles.themes import Colors


class LogHighlighter:
    """Destaque de sintaxe para logs."""

    PATTERNS = [
        (re.compile(r"\b(SEVERE|ERROR|FATAL)\b", re.IGNORECASE), QColor(Colors.ERROR)),
        (re.compile(r"\b(WARNING|WARN)\b", re.IGNORECASE), QColor(Colors.WARNING)),
        (re.compile(r"\b(INFO)\b", re.IGNORECASE), QColor(Colors.SUCCESS)),
        (re.compile(r"\b(FINE|FINER|FINEST|DEBUG)\b", re.IGNORECASE), QColor(Colors.TEXT_SECONDARY)),
        (re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", re.IGNORECASE), QColor(Colors.PRIMARY_LIGHT)),
        (re.compile(r"\b(server|domain1|glassfish)\b", re.IGNORECASE), QColor(Colors.PRIMARY)),
    ]

    @classmethod
    def highlight(cls, text: str) -> list[tuple[re.Pattern, QColor]]:
        """Retorna os padrões encontrados no texto."""
        matches = []
        for pattern, color in cls.PATTERNS:
            if pattern.search(text):
                matches.append((pattern, color))
        return matches


class LogViewer(QFrame):
    """Visualizador de logs com filtro e destaque."""

    log_filtered = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._log_path: Path | None = None
        self._last_position = 0
        self._filter_text = ""
        self._auto_scroll = True
        self._total_lines = 0
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self) -> None:
        """Configura a interface do visualizador."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            LogViewer {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        title = QLabel("Logs do Servidor")
        title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {Colors.TEXT_PRIMARY};
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._line_count_label = QLabel("0 linhas")
        self._line_count_label.setStyleSheet(f"""
            font-size: 11px;
            color: {Colors.TEXT_SECONDARY};
        """)
        header_layout.addWidget(self._line_count_label)

        layout.addLayout(header_layout)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("Filtrar logs...")
        self._filter_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {Colors.PRIMARY};
            }}
        """)
        self._filter_input.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._filter_input)

        self._clear_button = QPushButton("Limpar")
        self._clear_button.setFixedWidth(80)
        self._clear_button.clicked.connect(self._clear_logs)
        filter_layout.addWidget(self._clear_button)

        self._auto_scroll_button = QPushButton("Auto-scroll")
        self._auto_scroll_button.setCheckable(True)
        self._auto_scroll_button.setChecked(True)
        self._auto_scroll_button.setFixedWidth(100)
        self._auto_scroll_button.clicked.connect(self._toggle_auto_scroll)
        filter_layout.addWidget(self._auto_scroll_button)

        layout.addLayout(filter_layout)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 10))
        self._log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1a1a1a;
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self._log_text)

    def _setup_timer(self) -> None:
        """Configura o timer para atualização dos logs."""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_logs)
        self._timer.start(GlassFishConfig.LOG_TAIL_INTERVAL_MS)

    def set_log_path(self, path: Path) -> None:
        """Define o caminho do arquivo de log."""
        self._log_path = path
        self._last_position = 0
        self._log_text.clear()
        self._load_initial_logs()

    def _load_initial_logs(self) -> None:
        """Carrega as últimas linhas do log."""
        if not self._log_path or not self._log_path.exists():
            return

        try:
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                max_lines = GlassFishConfig.MAX_LOG_LINES
                start_idx = max(0, len(lines) - max_lines)

                for line in lines[start_idx:]:
                    self._append_log_line(line.rstrip())

                self._last_position = self._log_path.stat().st_size
                self._total_lines = len(lines)
                self._update_line_count()

        except Exception as e:
            logger.error(f"Erro ao carregar logs iniciais: {e}")

    @Slot()
    def _update_logs(self) -> None:
        """Atualiza o log com novas linhas."""
        if not self._log_path or not self._log_path.exists():
            return

        try:
            current_size = self._log_path.stat().st_size
            if current_size < self._last_position:
                self._last_position = 0
                self._log_text.clear()

            if current_size == self._last_position:
                return

            with open(self._log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._last_position)
                new_lines = f.readlines()
                self._last_position = f.tell()

                for line in new_lines:
                    self._append_log_line(line.rstrip())
                    self._total_lines += 1

                self._update_line_count()

        except Exception as e:
            logger.debug(f"Erro ao atualizar logs: {e}")

    def _append_log_line(self, line: str) -> None:
        """Adiciona uma linha ao log."""
        if self._filter_text and self._filter_text.lower() not in line.lower():
            return

        self._log_text.append(line)

        if self._auto_scroll:
            cursor = self._log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._log_text.setTextCursor(cursor)

    def _on_filter_changed(self, text: str) -> None:
        """Callback quando o filtro é alterado."""
        self._filter_text = text
        self._log_text.clear()

        if self._log_path and self._log_path.exists():
            self._load_initial_logs()

    def _clear_logs(self) -> None:
        """Limpa a visualização dos logs."""
        self._log_text.clear()
        self._total_lines = 0
        self._update_line_count()

    def _toggle_auto_scroll(self, checked: bool) -> None:
        """Alterna o auto-scroll."""
        self._auto_scroll = checked

    def _update_line_count(self) -> None:
        """Atualiza o contador de linhas."""
        self._line_count_label.setText(f"{self._total_lines} linhas")

    def get_log_text(self) -> str:
        """Retorna todo o texto do log."""
        return self._log_text.toPlainText()

    def search_in_logs(self, pattern: str) -> int:
        """Busca no log e retorna o número de ocorrências."""
        text = self._log_text.toPlainText()
        count = text.lower().count(pattern.lower())

        if count > 0:
            self._log_text.moveCursor(QTextCursor.MoveOperation.Start)
            self._log_text.find(pattern)

        return count
