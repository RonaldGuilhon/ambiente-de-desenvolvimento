"""Configurações e caminhos do GlassFish Monitor."""

from pathlib import Path
import os


class GlassFishConfig:
    """Configurações centrais do GlassFish."""

    # Caminhos padrão do GlassFish
    DEFAULT_GLASSFISH_PATH = Path(r"C:\Program Files\glassfish-4.1.1")
    DOMAINS_DIR_NAME = "domains"
    DOMAIN_NAME = "domain1"
    ASADMIN_BAT = "asadmin.bat"
    GLASSFISH_JAR = "glassfish.jar"

    # Portas padrão
    ADMIN_PORT = 4848
    HTTP_PORT = 8080
    HTTPS_PORT = 8443

    # Configurações de monitoramento
    MONITOR_INTERVAL_MS = 2000  # Intervalo de coleta de métricas
    LOG_TAIL_INTERVAL_MS = 1000  # Intervalo de atualização dos logs
    MAX_LOG_LINES = 5000  # Máximo de linhas no visualizador de logs

    # Configurações de processo
    COMMAND_TIMEOUT = 30  # Timeout para comandos asadmin (segundos)
    STARTUP_TIMEOUT = 60  # Timeout para inicialização do GlassFish (segundos)

    @classmethod
    def get_glassfish_home(cls) -> Path:
        """Retorna o caminho raiz do GlassFish (onde está o asadmin.bat)."""
        env_path = os.environ.get("GLASSFISH_HOME")
        if env_path:
            return Path(env_path)
        return cls.DEFAULT_GLASSFISH_PATH

    @classmethod
    def get_glassfish_path(cls) -> Path:
        """Retorna o caminho do GlassFish (com subpasta glassfish se existir)."""
        home = cls.get_glassfish_home()
        glassfish_subdir = home / "glassfish"
        if glassfish_subdir.exists():
            return glassfish_subdir
        return home

    @classmethod
    def get_asadmin_path(cls) -> Path:
        """Retorna o caminho completo do asadmin.bat."""
        return cls.get_glassfish_path() / "bin" / cls.ASADMIN_BAT

    @classmethod
    def get_domains_dir(cls) -> Path:
        """Retorna o diretório de domínios."""
        return cls.get_glassfish_path() / cls.DOMAINS_DIR_NAME

    @classmethod
    def get_domain_dir(cls, domain_name: str | None = None) -> Path:
        """Retorna o diretório de um domínio específico."""
        name = domain_name or cls.DOMAIN_NAME
        return cls.get_domains_dir() / name

    @classmethod
    def get_domain_log_path(cls, domain_name: str | None = None) -> Path:
        """Retorna o caminho do log do domínio."""
        domain_dir = cls.get_domain_dir(domain_name)
        return domain_dir / "logs" / "server.log"

    @classmethod
    def get_domain_config_path(cls, domain_name: str | None = None) -> Path:
        """Retorna o caminho do domain.xml do domínio."""
        domain_dir = cls.get_domain_dir(domain_name)
        return domain_dir / "config" / "domain.xml"

    @classmethod
    def validate_glassfish_installation(cls) -> tuple[bool, str]:
        """Valida se o GlassFish está instalado corretamente."""
        home = cls.get_glassfish_home()
        gf_path = cls.get_glassfish_path()

        if not gf_path.exists():
            return False, (
                f"Diretório do GlassFish não encontrado: {gf_path}\n"
                f"Verifique se o GLASSFISH_HOME está configurado corretamente."
            )

        asadmin = cls.get_asadmin_path()
        if not asadmin.exists():
            return False, f"asadmin.bat não encontrado: {asadmin}"

        domains_dir = cls.get_domains_dir()
        if not domains_dir.exists():
            return False, f"Diretório de domínios não encontrado: {domains_dir}"

        info = (
            f"GlassFish encontrado em: {gf_path}\n"
            f"Asadmin: {asadmin}\n"
            f"Domínios: {domains_dir}"
        )
        return True, info
