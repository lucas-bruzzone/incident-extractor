"""Testes unitários para o rate limiter"""

import pytest
from unittest.mock import MagicMock
from fastapi import Request

from app.rate_limiter import (
    get_client_ip,
    RATE_LIMIT_EXTRACT,
)


class TestGetClientIp:
    """Testes para extração de IP do cliente"""

    def test_forwarded_ip(self):
        """Deve extrair IP do X-Forwarded-For"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = get_client_ip(request)
        assert result == "10.0.0.1"

    def test_single_forwarded_ip(self):
        """Deve lidar com um único IP no X-Forwarded-For"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "10.0.0.50"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = get_client_ip(request)
        assert result == "10.0.0.50"

    def test_no_forwarded_uses_client_host(self):
        """Deve usar client.host quando não há X-Forwarded-For"""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        result = get_client_ip(request)
        assert result == "192.168.1.100"

    def test_whitespace_trimmed(self):
        """Deve remover espaços do IP"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "  10.0.0.1  , 192.168.1.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = get_client_ip(request)
        assert result == "10.0.0.1"


class TestRateLimitConfig:
    """Testes para configuração do rate limit"""

    def test_default_extract_limit(self):
        """Deve ter limite padrão configurado"""
        assert RATE_LIMIT_EXTRACT is not None
        assert "/" in RATE_LIMIT_EXTRACT  # Formato "N/period"

    def test_extract_limit_format(self):
        """Limite deve estar em formato válido"""
        parts = RATE_LIMIT_EXTRACT.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit()  # Número de requests
        assert parts[1] in ["second", "minute", "hour", "day"]  # Período válido
