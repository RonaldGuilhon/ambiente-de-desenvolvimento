# GlassFish Monitor

Aplicação desktop para monitoramento e controle do GlassFish Server.

## Funcionalidades

- **Status do Servidor**: Monitora o status do GlassFish em tempo real
- **Controles**: Iniciar, parar e reiniciar o servidor
- **Monitoramento de Recursos**: CPU, memória, threads e conexões
- **Logs em Tempo Real**: Visualização e filtro de logs do servidor
- **Interface Moderna**: Design escuro com PySide6

## Pré-requisitos

- Python 3.10+
- GlassFish 4.1.1 instalado em `C:\Program Files\glassfish-4.1.1\glassfish`
- Windows 10/11

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/glassfish-monitor.git
cd glassfish-monitor

# Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# Instalar dependências
pip install -e .

# Ou instalar dependências de desenvolvimento
pip install -e ".[dev]"
```

## Uso

### Executar com script (recomendado)

```bash
# Windows CMD
run.bat

# PowerShell
.\run.ps1
```

### Executar manualmente

```bash
# Ativar ambiente virtual
.venv\Scripts\activate

# Executar a aplicação
python -m glassfish_monitor

# Ou via entry point
glassfish-monitor
```

## Estrutura do Projeto

```
glassfish-monitor/
├── src/
│   └── glassfish_monitor/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       ├── services/
│       │   ├── glassfish_service.py
│       │   ├── monitor_service.py
│       │   └── process_manager.py
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── tabs/
│       │   │   ├── glassfish_tab.py
│       │   │   └── future_tab.py
│       │   ├── widgets/
│       │   │   ├── status_widget.py
│       │   │   ├── log_viewer.py
│       │   │   └── metrics_panel.py
│       │   └── styles/
│       │       └── themes.py
│       └── utils/
│           ├── logger.py
│           └── platform_utils.py
├── tests/
├── pyproject.toml
└── README.md
```

## Desenvolvimento

### Executar testes

```bash
pytest tests/
```

### Formatar código

```bash
ruff format src/ tests/
```

### Verificar lint

```bash
ruff check src/ tests/
```

### Type checking

```bash
mypy src/
```

## Configuração

A aplicação pode ser configurada via variáveis de ambiente:

- `GLASSFISH_HOME`: Caminho personalizado do GlassFish

Ou editando `src/glassfish_monitor/config.py`.

## Licença

MIT License
