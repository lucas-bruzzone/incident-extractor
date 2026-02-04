from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def normalize_date(value: str) -> Optional[str]:
    """
    Tenta normalizar diferentes formatos de data para YYYY-MM-DD HH:MM
    Retorna None se não conseguir parsear
    """
    if not value or value.lower() == "null":
        return None

    value = value.strip()

    # Já está no formato correto
    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", value):
        return value

    # Formatos comuns que o LLM pode retornar
    formats_to_try = [
        "%Y-%m-%dT%H:%M:%S",  # ISO format
        "%Y-%m-%dT%H:%M",  # ISO without seconds
        "%d/%m/%Y %H:%M",  # BR format
        "%d/%m/%Y %H:%M:%S",  # BR format with seconds
        "%Y-%m-%d %H:%M:%S",  # Standard with seconds
        "%d-%m-%Y %H:%M",  # BR with dashes
        "%Y/%m/%d %H:%M",  # Alternative
    ]

    for fmt in formats_to_try:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue

    # Tenta extrair apenas data (sem hora)
    date_only_formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    for fmt in date_only_formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m-%d") + " 00:00"
        except ValueError:
            continue

    logger.warning(f"Não foi possível normalizar data: {value}")
    return None


class IncidentRequest(BaseModel):
    """Schema de entrada para descricao do incidente"""

    descricao: str = Field(
        ..., min_length=10, description="Descricao textual do incidente"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "descricao": "Ontem as 14h, no escritorio de Sao Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
            }
        }
    )


class IncidentResponse(BaseModel):
    """Schema de saida com informacoes extraidas do incidente"""

    data_ocorrencia: Optional[str] = Field(
        None, description="Data e hora do incidente no formato YYYY-MM-DD HH:MM"
    )
    local: Optional[str] = Field(None, description="Local onde o incidente ocorreu")
    tipo_incidente: Optional[str] = Field(
        None, description="Tipo ou categoria do incidente"
    )
    impacto: Optional[str] = Field(
        None, description="Descricao breve do impacto gerado"
    )

    @field_validator("data_ocorrencia", mode="before")
    @classmethod
    def validate_and_normalize_date(cls, v):
        """Valida e normaliza o formato da data"""
        if v is None:
            return None
        return normalize_date(str(v))

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data_ocorrencia": "2025-02-03 14:00",
                "local": "Sao Paulo",
                "tipo_incidente": "Falha no servidor",
                "impacto": "Sistema de faturamento indisponivel por 2 horas",
            }
        }
    )
