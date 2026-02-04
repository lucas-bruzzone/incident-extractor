"""Configuração de logging estruturado JSON para produção"""

import logging
import sys
from datetime import datetime, timezone
from typing import Any
import json


class JSONFormatter(logging.Formatter):
    """Formatter que gera logs em JSON estruturado"""

    def __init__(self, service_name: str = "incident-extractor"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }

        # Adiciona informações de localização
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Adiciona exceção se existir
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Adiciona campos extras do record
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "taskName",
                "message",
            }
        }

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, ensure_ascii=False, default=str)


class RequestContextFilter(logging.Filter):
    """Filter que adiciona contexto de request aos logs"""

    def __init__(self):
        super().__init__()
        self._request_id = None
        self._endpoint = None

    def set_context(self, request_id: str = None, endpoint: str = None):
        """Define o contexto da request atual"""
        self._request_id = request_id
        self._endpoint = endpoint

    def clear_context(self):
        """Limpa o contexto"""
        self._request_id = None
        self._endpoint = None

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self._request_id
        record.endpoint = self._endpoint
        return True


# Instância global do filtro de contexto
request_context_filter = RequestContextFilter()


def setup_logging(level: str = "INFO") -> None:
    """
    Configura logging estruturado JSON para toda a aplicação

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove handlers existentes
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Configura handler com JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(request_context_filter)

    # Configura root logger
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(handler)

    # Reduz verbosidade de loggers de terceiros
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Retorna logger configurado para o módulo

    Args:
        name: Nome do módulo (geralmente __name__)

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)
