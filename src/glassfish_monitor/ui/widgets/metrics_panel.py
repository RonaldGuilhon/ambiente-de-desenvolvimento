"""Painel de métricas com gráficos em tempo real."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from glassfish_monitor.services.monitor_service import MetricsHistory, ResourceMetrics
from glassfish_monitor.ui.styles.themes import Colors

try:
    import pyqtgraph as pg

    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False


class MetricCard(QFrame):
    """Card de exibição de uma métrica."""

    def __init__(self, title: str, unit: str = "", parent=None) -> None:
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do card."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: {Colors.SURFACE_LIGHT};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            font-size: 11px;
            color: {Colors.TEXT_SECONDARY};
            font-weight: bold;
        """)
        layout.addWidget(title_label)

        self._value_label = QLabel(f"0{self._unit}")
        self._value_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        layout.addWidget(self._value_label)

    def update_value(self, value: float | int) -> None:
        """Atualiza o valor exibido."""
        if isinstance(value, float):
            self._value_label.setText(f"{value:.1f}{self._unit}")
        else:
            self._value_label.setText(f"{value}{self._unit}")

    def set_color(self, color: str) -> None:
        """Define a cor do valor."""
        self._value_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {color};
        """)


class MetricsPanel(QFrame):
    """Painel de métricas com cards e gráficos."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do painel."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            MetricsPanel {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        title = QLabel("Monitoramento de Recursos")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {Colors.TEXT_PRIMARY};
        """)
        main_layout.addWidget(title)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._cpu_card = MetricCard("CPU", "%")
        self._cpu_card.set_color(Colors.PRIMARY)
        cards_layout.addWidget(self._cpu_card)

        self._memory_card = MetricCard("Memória", "%")
        self._memory_card.set_color(Colors.SUCCESS)
        cards_layout.addWidget(self._memory_card)

        self._memory_mb_card = MetricCard("Memória", "MB")
        self._memory_mb_card.set_color(Colors.WARNING)
        cards_layout.addWidget(self._memory_mb_card)

        self._threads_card = MetricCard("Threads", "")
        self._threads_card.set_color(Colors.PRIMARY_LIGHT)
        cards_layout.addWidget(self._threads_card)

        self._connections_card = MetricCard("Conexões", "")
        self._connections_card.set_color(Colors.SUCCESS)
        cards_layout.addWidget(self._connections_card)

        self._files_card = MetricCard("Arquivos", "abertos")
        self._files_card.set_color(Colors.WARNING)
        cards_layout.addWidget(self._files_card)

        main_layout.addLayout(cards_layout)

        if HAS_PYQTGRAPH:
            self._setup_graphs(main_layout)
        else:
            no_graph_label = QLabel(
                "pyqtgraph não instalado - gráficos indisponíveis\n"
                "Instale com: pip install pyqtgraph"
            )
            no_graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_graph_label.setStyleSheet(f"""
                color: {Colors.TEXT_SECONDARY};
                padding: 20px;
            """)
            main_layout.addWidget(no_graph_label)

    def _setup_graphs(self, layout: QVBoxLayout) -> None:
        """Configura os gráficos de métricas."""
        pg.setConfigOptions(antialias=True)

        graph_layout = QHBoxLayout()
        graph_layout.setSpacing(12)

        cpu_group = QGroupBox("CPU (%)")
        cpu_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                margin-top: 1em;
                padding-top: 10px;
                font-weight: bold;
                color: {Colors.TEXT_PRIMARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        cpu_layout = QVBoxLayout(cpu_group)

        self._cpu_plot = pg.PlotWidget()
        self._cpu_plot.setBackground("#1a1a1a")
        self._cpu_plot.showGrid(x=True, y=True, alpha=0.3)
        self._cpu_plot.setYRange(0, 100)
        self._cpu_plot.setLabel("left", "CPU", "%")
        self._cpu_curve = self._cpu_plot.plot(pen=pg.mkPen(Colors.PRIMARY, width=2))
        cpu_layout.addWidget(self._cpu_plot)
        graph_layout.addWidget(cpu_group)

        mem_group = QGroupBox("Memória (%)")
        mem_group.setStyleSheet(cpu_group.styleSheet())
        mem_layout = QVBoxLayout(mem_group)

        self._mem_plot = pg.PlotWidget()
        self._mem_plot.setBackground("#1a1a1a")
        self._mem_plot.showGrid(x=True, y=True, alpha=0.3)
        self._mem_plot.setYRange(0, 100)
        self._mem_plot.setLabel("left", "Memória", "%")
        self._mem_curve = self._mem_plot.plot(pen=pg.mkPen(Colors.SUCCESS, width=2))
        mem_layout.addWidget(self._mem_plot)
        graph_layout.addWidget(mem_group)

        threads_group = QGroupBox("Threads")
        threads_group.setStyleSheet(cpu_group.styleSheet())
        threads_layout = QVBoxLayout(threads_group)

        self._threads_plot = pg.PlotWidget()
        self._threads_plot.setBackground("#1a1a1a")
        self._threads_plot.showGrid(x=True, y=True, alpha=0.3)
        self._threads_plot.setLabel("left", "Threads", "")
        self._threads_curve = self._threads_plot.plot(pen=pg.mkPen(Colors.WARNING, width=2))
        threads_layout.addWidget(self._threads_plot)
        graph_layout.addWidget(threads_group)

        layout.addLayout(graph_layout)

    def update_metrics(self, metrics: ResourceMetrics) -> None:
        """Atualiza todas as métricas exibidas."""
        self._cpu_card.update_value(metrics.cpu_percent)
        self._memory_card.update_value(metrics.memory_percent)
        self._memory_mb_card.update_value(metrics.memory_mb)
        self._threads_card.update_value(metrics.threads)
        self._connections_card.update_value(metrics.connections)
        self._files_card.update_value(metrics.open_files)

        if metrics.cpu_percent > 80:
            self._cpu_card.set_color(Colors.ERROR)
        elif metrics.cpu_percent > 60:
            self._cpu_card.set_color(Colors.WARNING)
        else:
            self._cpu_card.set_color(Colors.PRIMARY)

        if metrics.memory_percent > 80:
            self._memory_card.set_color(Colors.ERROR)
        elif metrics.memory_percent > 60:
            self._memory_card.set_color(Colors.WARNING)
        else:
            self._memory_card.set_color(Colors.SUCCESS)

    def update_graphs(self, history: MetricsHistory) -> None:
        """Atualiza os gráficos com o histórico."""
        if not HAS_PYQTGRAPH:
            return

        if history.cpu:
            self._cpu_curve.setData(list(history.cpu))
        if history.memory:
            self._mem_curve.setData(list(history.memory))
        if history.threads:
            self._threads_curve.setData(list(history.threads))

    def clear(self) -> None:
        """Limpa todas as métricas."""
        self._cpu_card.update_value(0)
        self._memory_card.update_value(0)
        self._memory_mb_card.update_value(0)
        self._threads_card.update_value(0)
        self._connections_card.update_value(0)
        self._files_card.update_value(0)

        if HAS_PYQTGRAPH:
            self._cpu_curve.setData([])
            self._mem_curve.setData([])
            self._threads_curve.setData([])
