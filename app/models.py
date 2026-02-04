from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class IncidentRequest(BaseModel):
    """Schema de entrada para descricao do incidente"""
    descricao: str = Field(
        ...,
        min_length=10,
        description="Descricao textual do incidente"
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
        None,
        description="Data e hora do incidente no formato YYYY-MM-DD HH:MM"
    )
    local: Optional[str] = Field(
        None,
        description="Local onde o incidente ocorreu"
    )
    tipo_incidente: Optional[str] = Field(
        None,
        description="Tipo ou categoria do incidente"
    )
    impacto: Optional[str] = Field(
        None,
        description="Descricao breve do impacto gerado"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data_ocorrencia": "2025-02-03 14:00",
                "local": "Sao Paulo",
                "tipo_incidente": "Falha no servidor",
                "impacto": "Sistema de faturamento indisponivel por 2 horas"
            }
        }
    )