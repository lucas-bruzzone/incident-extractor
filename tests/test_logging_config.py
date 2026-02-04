"""Testes unitários para o módulo de logging estruturado"""

import pytest
import logging
import json
from io import StringIO
from datetime import datetime

from app.logging_config import (
    JSONFormatter,
    RequestContextFilter,
    setup_logging,
    get_logger,
    request_context_filter,
)


class TestJSONFormatter:
    """Testes para o formatter JSON"""

    def test_format_basic_message(self):
        """Deve formatar mensagem básica em JSON"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_format_includes_location(self):
        """Deve incluir informações de localização"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"

        result = formatter.format(record)
        data = json.loads(result)

        assert "location" in data
        assert data["location"]["line"] == 42
        assert data["location"]["function"] == "test_function"

    def test_format_includes_service_name(self):
        """Deve incluir nome do serviço"""
        formatter = JSONFormatter(service_name="my-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["service"] == "my-service"

    def test_format_with_exception(self):
        """Deve incluir exceção quando presente"""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_format_with_extra_fields(self):
        """Deve incluir campos extras"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc-123"
        record.custom_field = "custom_value"

        result = formatter.format(record)
        data = json.loads(result)

        assert "extra" in data
        assert data["extra"]["request_id"] == "abc-123"
        assert data["extra"]["custom_field"] == "custom_value"

    def test_timestamp_format(self):
        """Timestamp deve estar em formato ISO com Z"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["timestamp"].endswith("Z")
        # Deve ser parseável
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestRequestContextFilter:
    """Testes para o filtro de contexto de request"""

    def test_set_and_clear_context(self):
        """Deve definir e limpar contexto"""
        filter = RequestContextFilter()

        filter.set_context(request_id="req-123", endpoint="/test")
        assert filter._request_id == "req-123"
        assert filter._endpoint == "/test"

        filter.clear_context()
        assert filter._request_id is None
        assert filter._endpoint is None

    def test_filter_adds_context_to_record(self):
        """Deve adicionar contexto ao record"""
        filter = RequestContextFilter()
        filter.set_context(request_id="req-456", endpoint="/api/test")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter.filter(record)

        assert result is True
        assert record.request_id == "req-456"
        assert record.endpoint == "/api/test"

    def test_filter_with_no_context(self):
        """Deve funcionar sem contexto definido"""
        filter = RequestContextFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter.filter(record)

        assert result is True
        assert record.request_id is None
        assert record.endpoint is None


class TestSetupLogging:
    """Testes para configuração do logging"""

    def test_setup_configures_root_logger(self):
        """Deve configurar root logger"""
        setup_logging(level="DEBUG")
        root = logging.getLogger()

        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1

    def test_setup_with_info_level(self):
        """Deve aceitar nível INFO"""
        setup_logging(level="INFO")
        root = logging.getLogger()

        assert root.level == logging.INFO

    def test_get_logger_returns_logger(self):
        """Deve retornar logger configurado"""
        setup_logging()
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"


class TestGlobalContextFilter:
    """Testes para o filtro global"""

    def test_global_filter_exists(self):
        """Filtro global deve existir"""
        assert request_context_filter is not None
        assert isinstance(request_context_filter, RequestContextFilter)
