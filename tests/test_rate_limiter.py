"""Testes unitários para o rate limiter"""

import pytest
from unittest.mock import MagicMock
from fastapi import Request
from slowapi.errors import RateLimitExceeded

from app.rate_limiter import (
    get_client_ip,
    rate_limit_exceeded_handler,
    RATE_LIMIT_EXTRACT,
)


class TestGetClientIp:
    """Testes para extração de IP do cliente"""

    def test_direct_ip(self):
        """Deve retornar IP direto quando não há proxy"""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        # Simula comportamento do get_remote_address
        from slowapi.util import get_remote_address

        result = get_remote_address(request)
        assert result == "192.168.1.100"

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


class TestRateLimitExceededHandler:
    """Testes para o handler de rate limit excedido"""

    @pytest.mark.asyncio
    async def test_returns_429(self):
        """Deve retornar status 429"""
        request = MagicMock(spec=Request)
        exc = RateLimitExceeded("10 per 1 minute")

        response = await rate_limit_exceeded_handler(request, exc)

        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_response_format(self):
        """Deve retornar JSON com formato correto"""
        request = MagicMock(spec=Request)
        exc = RateLimitExceeded("10 per 1 minute")

        response = await rate_limit_exceeded_handler(request, exc)
        body = response.body.decode()

        assert "rate_limit_exceeded" in body
        assert "error" in body
        assert "message" in body
        assert "suggestion" in body

    @pytest.mark.asyncio
    async def test_retry_after_header(self):
        """Deve incluir header Retry-After"""
        request = MagicMock(spec=Request)
        exc = RateLimitExceeded("10 per 1 minute")

        response = await rate_limit_exceeded_handler(request, exc)

        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers


class TestRateLimitConfig:
    """Testes para configuração do rate limit"""

    def test_default_extract_limit(self):
        """Deve ter limite padrão configurado"""
        assert RATE_LIMIT_EXTRACT is not None
        assert "/" in RATE_LIMIT_EXTRACT  # Formato "N/period"
