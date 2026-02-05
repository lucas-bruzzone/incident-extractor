"""Testes unitários para o módulo de configuração"""

import pytest
import os
from unittest.mock import patch

from app.config import Settings, get_settings


class TestSettings:
    """Testes para a classe Settings"""

    def test_default_values(self):
        """Deve usar valores padrão quando variáveis não definidas"""
        # Limpa cache para forçar nova instância
        get_settings.cache_clear()

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_model == "qwen2:0.5b"
        assert settings.ollama_timeout == 180.0
        assert settings.ollama_max_retries == 3
        assert settings.rate_limit_extract == "10/minute"
        assert settings.rate_limit_default == "60/minute"
        assert settings.log_level == "INFO"

    def test_env_override(self):
        """Deve sobrescrever valores com variáveis de ambiente"""
        get_settings.cache_clear()

        env_vars = {
            "OLLAMA_BASE_URL": "http://custom:9999",
            "OLLAMA_MODEL": "custom-model",
            "OLLAMA_TIMEOUT": "60.0",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

        assert settings.ollama_base_url == "http://custom:9999"
        assert settings.ollama_model == "custom-model"
        assert settings.ollama_timeout == 60.0
        assert settings.log_level == "DEBUG"

    def test_log_level_validation_valid(self):
        """Deve aceitar níveis de log válidos"""
        get_settings.cache_clear()

        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            with patch.dict(os.environ, {"LOG_LEVEL": level}, clear=True):
                settings = Settings()
                assert settings.log_level == level

    def test_log_level_validation_case_insensitive(self):
        """Deve aceitar níveis de log em qualquer case"""
        get_settings.cache_clear()

        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}, clear=True):
            settings = Settings()
            assert settings.log_level == "DEBUG"

    def test_log_level_validation_invalid(self):
        """Deve rejeitar níveis de log inválidos"""
        get_settings.cache_clear()

        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "log_level" in str(exc_info.value).lower()

    def test_rate_limit_validation_valid(self):
        """Deve aceitar formatos de rate limit válidos"""
        get_settings.cache_clear()

        valid_formats = ["10/minute", "100/hour", "5/second", "1000/day"]

        for fmt in valid_formats:
            with patch.dict(os.environ, {"RATE_LIMIT_EXTRACT": fmt}, clear=True):
                settings = Settings()
                assert settings.rate_limit_extract == fmt

    def test_rate_limit_validation_invalid_format(self):
        """Deve rejeitar formatos de rate limit inválidos"""
        get_settings.cache_clear()

        invalid_formats = ["10", "10-minute", "abc/minute", "10/week"]

        for fmt in invalid_formats:
            with patch.dict(os.environ, {"RATE_LIMIT_EXTRACT": fmt}, clear=True):
                with pytest.raises(ValueError):
                    Settings()

    def test_timeout_bounds(self):
        """Deve validar limites do timeout"""
        get_settings.cache_clear()

        # Valor válido
        with patch.dict(os.environ, {"OLLAMA_TIMEOUT": "300"}, clear=True):
            settings = Settings()
            assert settings.ollama_timeout == 300.0

    def test_max_retries_bounds(self):
        """Deve validar limites de max_retries"""
        get_settings.cache_clear()

        # Valor válido
        with patch.dict(os.environ, {"OLLAMA_MAX_RETRIES": "5"}, clear=True):
            settings = Settings()
            assert settings.ollama_max_retries == 5


class TestGetSettings:
    """Testes para a função get_settings"""

    def test_returns_settings_instance(self):
        """Deve retornar instância de Settings"""
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_cached_singleton(self):
        """Deve retornar mesma instância (cache)"""
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_cache_clear_creates_new_instance(self):
        """Deve criar nova instância após limpar cache"""
        settings1 = get_settings()
        get_settings.cache_clear()
        settings2 = get_settings()

        # São instâncias diferentes (ids diferentes)
        assert settings1 is not settings2


class TestSettingsIntegration:
    """Testes de integração das configurações"""

    def test_cors_origins_list(self):
        """Deve aceitar lista de origens CORS"""
        get_settings.cache_clear()

        settings = Settings()
        assert isinstance(settings.cors_origins, list)
        assert "*" in settings.cors_origins

    def test_validation_flags(self):
        """Deve ter flags de validação configuráveis"""
        get_settings.cache_clear()

        settings = Settings()
        assert settings.validate_llm_response is True
        assert settings.allow_partial_response is True

    def test_api_metadata(self):
        """Deve ter metadados da API"""
        get_settings.cache_clear()

        settings = Settings()
        assert settings.api_title == "Incident Information Extractor API"
        assert settings.api_version == "1.0.0"
        assert settings.service_name == "incident-extractor"
