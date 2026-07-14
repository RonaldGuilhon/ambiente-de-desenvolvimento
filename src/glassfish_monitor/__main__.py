"""Ponto de entrada da aplicação GlassFish Monitor."""

import sys


def main() -> None:
    """Função principal de inicialização."""
    from glassfish_monitor.app import run

    sys.exit(run())


if __name__ == "__main__":
    main()
