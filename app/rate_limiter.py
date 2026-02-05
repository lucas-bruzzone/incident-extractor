"""Configuração de rate limiting para a API"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

from app.config import get_settings


def get_client_ip(request: Request) -> str:
    """
    Extrai IP do cliente considerando proxies (X-Forwarded-For)
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Instância global do limiter
limiter = Limiter(key_func=get_client_ip)


def get_rate_limit_extract() -> str:
    """Retorna limite de rate para endpoint extract"""
    return get_settings().rate_limit_extract


def get_rate_limit_default() -> str:
    """Retorna limite de rate padrão"""
    return get_settings().rate_limit_default


# Exportar para uso direto (compatibilidade)
RATE_LIMIT_EXTRACT = get_settings().rate_limit_extract
RATE_LIMIT_DEFAULT = get_settings().rate_limit_default


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Handler customizado para erro de rate limit
    Retorna resposta JSON consistente com outros erros da API
    """
    settings = get_settings()

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Limite de requisições excedido",
            "details": str(exc.detail),
            "suggestion": "Aguarde alguns instantes antes de tentar novamente",
        },
        headers={
            "Retry-After": str(exc.detail.split()[-1]) if exc.detail else "60",
            "X-RateLimit-Limit": settings.rate_limit_extract,
        },
    )


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configura rate limiting na aplicação FastAPI

    Args:
        app: Instância da aplicação FastAPI
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
