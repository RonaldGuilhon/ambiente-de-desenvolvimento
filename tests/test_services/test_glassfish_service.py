"""Testes do GlassFish Service."""

import pytest

from glassfish_monitor.config import GlassFishConfig
from glassfish_monitor.services.glassfish_service import (
    DomainInfo,
    GlassFishService,
    ServerStatus,
)


class TestGlassFishConfig:
    """Testes da configuração do GlassFish."""

    def test_default_glassfish_path(self):
        """Testa se o caminho padrão do GlassFish está correto."""
        path = GlassFishConfig.get_glassfish_path()
        assert "glassfish" in str(path).lower()

    def test_asadmin_path(self):
        """Testa se o caminho do asadmin está correto."""
        asadmin = GlassFishConfig.get_asadmin_path()
        assert asadmin.name == "asadmin.bat"

    def test_domains_dir(self):
        """Testa se o diretório de domínios está correto."""
        domains_dir = GlassFishConfig.get_domains_dir()
        assert domains_dir.name == "domains"


class TestServerStatus:
    """Testes do enum ServerStatus."""

    def test_status_values(self):
        """Testa se os valores do enum estão corretos."""
        assert ServerStatus.RUNNING.value == "running"
        assert ServerStatus.STOPPED.value == "stopped"
        assert ServerStatus.RESTART_REQUIRED.value == "restart_required"
        assert ServerStatus.UNKNOWN.value == "unknown"
        assert ServerStatus.ERROR.value == "error"


class TestDomainInfo:
    """Testes da classe DomainInfo."""

    def test_domain_info_creation(self):
        """Testa a criação de um DomainInfo."""
        info = DomainInfo(
            name="domain1",
            status=ServerStatus.RUNNING,
            admin_port=4848,
            http_port=8080,
        )
        assert info.name == "domain1"
        assert info.status == ServerStatus.RUNNING
        assert info.admin_port == 4848
        assert info.http_port == 8080


class TestGlassFishService:
    """Testes do GlassFishService."""

    def test_service_creation(self, qapp_instance):
        """Testa a criação do serviço."""
        service = GlassFishService()
        assert service.domain_name == "domain1"
        assert service.current_status == ServerStatus.UNKNOWN

    def test_service_custom_domain(self, qapp_instance):
        """Testa a criação do serviço com domínio customizado."""
        service = GlassFishService(domain_name="custom_domain")
        assert service.domain_name == "custom_domain"
