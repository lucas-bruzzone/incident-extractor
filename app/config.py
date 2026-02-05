"""Configuração centralizada da aplicação usando pydantic-settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas de variáveis de ambiente.

    Todas as configurações podem ser sobrescritas via variáveis de ambiente
    ou arquivo .env na raiz do projeto.
    """

    # Ollama LLM Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="URL base do serviço Ollama",
    )
    ollama_model: str = Field(
        default="qwen2:0.5b",
        description="Nome do modelo a ser utilizado",
    )
    ollama_timeout: float = Field(
        default=180.0,
        ge=1.0,
        le=600.0,
        description="Timeout em segundos para requisições ao Ollama",
    )
    ollama_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Número máximo de tentativas em caso de falha",
    )

    # Rate Limiting Configuration
    rate_limit_extract: str = Field(
        default="10/minute",
        description="Limite de requisições para /extract-incident",
    )
    rate_limit_default: str = Field(
        default="60/minute",
        description="Limite padrão de requisições para outros endpoints",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    service_name: str = Field(
        default="incident-extractor",
        description="Nome do serviço para logs estruturados",
    )

    # API Configuration
    api_title: str = Field(
        default="Incident Information Extractor API",
        description="Título da API para documentação",
    )
    api_version: str = Field(
        default="1.0.0",
        description="Versão da API",
    )
    cors_origins: list[str] = Field(
        default=["*"],
        description="Origens permitidas para CORS",
    )

    # LLM Response Validation
    validate_llm_response: bool = Field(
        default=True,
        description="Habilita validação de schema na resposta do LLM",
    )
    allow_partial_response: bool = Field(
        default=True,
        description="Permite respostas com campos faltando (serão null)",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valida e normaliza o nível de log"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"log_level deve ser um de: {valid_levels}")
        return upper_v

    @field_validator("rate_limit_extract", "rate_limit_default")
    @classmethod
    def validate_rate_limit_format(cls, v: str) -> str:
        """Valida formato do rate limit (N/period)"""
        valid_periods = {"second", "minute", "hour", "day"}
        parts = v.split("/")
        if len(parts) != 2:
            raise ValueError("Formato deve ser 'N/period' (ex: 10/minute)")
        if not parts[0].isdigit():
            raise ValueError("Número de requisições deve ser inteiro")
        if parts[1] not in valid_periods:
            raise ValueError(f"Período deve ser um de: {valid_periods}")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.

    Usa cache para evitar recarregar configurações a cada chamada.
    Para testes, use `get_settings.cache_clear()` para resetar.
    """
    return Settings()
