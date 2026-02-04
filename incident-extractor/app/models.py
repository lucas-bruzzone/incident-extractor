from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class IncidentRequest(BaseModel):
    """Schema de entrada para descrição do incidente"""
    descricao: str = Field(
        ...,
        min_length=10,
        description="Descrição textual do incidente"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "descricao": "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
            }
        }


class IncidentResponse(BaseModel):
    """Schema de saída com informações extraídas do incidente"""
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
        description="Descrição breve do impacto gerado"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "data_ocorrencia": "2025-02-03 14:00",
                "local": "São Paulo",
                "tipo_incidente": "Falha no servidor",
                "impacto": "Sistema de faturamento indisponível por 2 horas"
            }
        }
