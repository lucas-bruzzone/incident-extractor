"""Testes unitarios para as excecoes customizadas"""

import pytest
from app.exceptions import (
    IncidentExtractorError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMResponseError,
    JSONParsingError,
    PreprocessingError,
)


class TestIncidentExtractorError:
    """Testes para a excecao base"""

    def test_message_only(self):
        """Deve criar excecao apenas com mensagem"""
        exc = IncidentExtractorError("Erro de teste")
        assert exc.message == "Erro de teste"
        assert exc.details is None
        assert str(exc) == "Erro de teste"

    def test_message_and_details(self):
        """Deve criar excecao com mensagem e detalhes"""
        exc = IncidentExtractorError("Erro", "Detalhes do erro")
        assert exc.message == "Erro"
        assert exc.details == "Detalhes do erro"


class TestLLMConnectionError:
    """Testes para erro de conexao"""

    def test_default_message(self):
        """Deve usar mensagem padrao"""
        exc = LLMConnectionError()
        assert "conectar" in exc.message.lower()

    def test_custom_message(self):
        """Deve aceitar mensagem customizada"""
        exc = LLMConnectionError("Custom error", "host unreachable")
        assert exc.message == "Custom error"
        assert exc.details == "host unreachable"

    def test_inheritance(self):
        """Deve herdar de IncidentExtractorError"""
        exc = LLMConnectionError()
        assert isinstance(exc, IncidentExtractorError)


class TestLLMTimeoutError:
    """Testes para erro de timeout"""

    def test_default_message(self):
        """Deve usar mensagem padrao"""
        exc = LLMTimeoutError()
        assert "timeout" in exc.message.lower()

    def test_inheritance(self):
        """Deve herdar de IncidentExtractorError"""
        exc = LLMTimeoutError()
        assert isinstance(exc, IncidentExtractorError)


class TestLLMResponseError:
    """Testes para erro de resposta"""

    def test_default_message(self):
        """Deve usar mensagem padrao"""
        exc = LLMResponseError()
        assert "resposta" in exc.message.lower() or "invalid" in exc.message.lower()

    def test_inheritance(self):
        """Deve herdar de IncidentExtractorError"""
        exc = LLMResponseError()
        assert isinstance(exc, IncidentExtractorError)


class TestJSONParsingError:
    """Testes para erro de parsing JSON"""

    def test_default_message(self):
        """Deve usar mensagem padrao"""
        exc = JSONParsingError()
        assert "json" in exc.message.lower()

    def test_inheritance(self):
        """Deve herdar de LLMResponseError"""
        exc = JSONParsingError()
        assert isinstance(exc, LLMResponseError)
        assert isinstance(exc, IncidentExtractorError)


class TestPreprocessingError:
    """Testes para erro de preprocessamento"""

    def test_default_message(self):
        """Deve usar mensagem padrao"""
        exc = PreprocessingError()
        assert "pr" in exc.message.lower()  # pre-processar

    def test_inheritance(self):
        """Deve herdar de IncidentExtractorError"""
        exc = PreprocessingError()
        assert isinstance(exc, IncidentExtractorError)
