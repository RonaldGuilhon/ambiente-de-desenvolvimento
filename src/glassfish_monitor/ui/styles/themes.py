"""Estilos e temas da aplicação."""

from PySide6.QtGui import QColor, QFont, QPalette


class Colors:
    """Cores do tema."""

    PRIMARY = "#1976D2"
    PRIMARY_DARK = "#1565C0"
    PRIMARY_LIGHT = "#42A5F5"

    SUCCESS = "#4CAF50"
    SUCCESS_DARK = "#388E3C"

    WARNING = "#FF9800"
    WARNING_DARK = "#F57C00"

    ERROR = "#F44336"
    ERROR_DARK = "#D32F2F"

    BACKGROUND = "#1E1E1E"
    SURFACE = "#2D2D2D"
    SURFACE_LIGHT = "#3D3D3D"

    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0B0B0"
    TEXT_DISABLED = "#666666"

    BORDER = "#404040"


class GlassFishStyles:
    """Estilos específicos do GlassFish."""

    @staticmethod
    def get_status_indicator_color(status: str) -> str:
        """Retorna a cor do indicador de status."""
        color_map = {
            "running": Colors.SUCCESS,
            "stopped": Colors.ERROR,
            "restart_required": Colors.WARNING,
            "unknown": Colors.TEXT_DISABLED,
            "error": Colors.ERROR,
        }
        return color_map.get(status, Colors.TEXT_DISABLED)

    @staticmethod
    def get_stylesheet() -> str:
        """Retorna o stylesheet principal da aplicação."""
        return f"""
            QMainWindow {{
                background-color: {Colors.BACKGROUND};
            }}
            QWidget {{
                background-color: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QTabWidget::pane {{
                border: 1px solid {Colors.BORDER};
                background-color: {Colors.SURFACE};
            }}
            QTabBar::tab {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px 20px;
                border: 1px solid {Colors.BORDER};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.PRIMARY};
                color: {Colors.TEXT_PRIMARY};
            }}
            QTabBar::tab:hover {{
                background-color: {Colors.PRIMARY_DARK};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
            QPushButton:disabled {{
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_DISABLED};
            }}
            QPushButton#startButton {{
                background-color: {Colors.SUCCESS};
            }}
            QPushButton#startButton:hover {{
                background-color: {Colors.SUCCESS_DARK};
            }}
            QPushButton#stopButton {{
                background-color: {Colors.ERROR};
            }}
            QPushButton#stopButton:hover {{
                background-color: {Colors.ERROR_DARK};
            }}
            QPushButton#restartButton {{
                background-color: {Colors.WARNING};
            }}
            QPushButton#restartButton:hover {{
                background-color: {Colors.WARNING_DARK};
            }}
            QGroupBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                margin-top: 1em;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QTextEdit {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QProgressBar {{
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                text-align: center;
                background-color: {Colors.SURFACE};
            }}
            QProgressBar::chunk {{
                background-color: {Colors.PRIMARY};
                border-radius: 3px;
            }}
        """
