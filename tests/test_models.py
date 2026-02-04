"""Testes unitarios para os schemas Pydantic"""

import pytest
from pydantic import ValidationError
from app.models import IncidentRequest, IncidentResponse


class TestIncidentRequest:
    """Testes para o schema de entrada"""

    def test_valid_request(self):
        """Deve aceitar descricao valida"""
        request = IncidentRequest(descricao="Incidente de teste com texto suficiente")
        assert request.descricao == "Incidente de teste com texto suficiente"

    def test_min_length_validation(self):
        """Deve rejeitar descricao muito curta"""
        with pytest.raises(ValidationError) as exc_info:
            IncidentRequest(descricao="curto")
        assert "String should have at least 10 characters" in str(exc_info.value)

    def test_empty_description(self):
        """Deve rejeitar descricao vazia"""
        with pytest.raises(ValidationError):
            IncidentRequest(descricao="")

    def test_missing_description(self):
        """Deve rejeitar requisicao sem descricao"""
        with pytest.raises(ValidationError):
            IncidentRequest()


class TestIncidentResponse:
    """Testes para o schema de saida"""

    def test_full_response(self):
        """Deve aceitar resposta completa"""
        response = IncidentResponse(
            data_ocorrencia="2025-02-03 14:00",
            local="Sao Paulo",
            tipo_incidente="Falha no servidor",
            impacto="Sistema indisponivel"
        )
        assert response.data_ocorrencia == "2025-02-03 14:00"
        assert response.local == "Sao Paulo"
        assert response.tipo_incidente == "Falha no servidor"
        assert response.impacto == "Sistema indisponivel"

    def test_partial_response(self):
        """Deve aceitar resposta parcial com campos None"""
        response = IncidentResponse(
            data_ocorrencia=None,
            local=None,
            tipo_incidente="Vazamento de dados",
            impacto="Dados comprometidos"
        )
        assert response.data_ocorrencia is None
        assert response.local is None
        assert response.tipo_incidente == "Vazamento de dados"

    def test_empty_response(self):
        """Deve aceitar resposta com todos os campos None"""
        response = IncidentResponse()
        assert response.data_ocorrencia is None
        assert response.local is None
        assert response.tipo_incidente is None
        assert response.impacto is None

    def test_response_to_dict(self):
        """Deve converter corretamente para dicionario"""
        response = IncidentResponse(
            data_ocorrencia="2025-02-03 14:00",
            local="Sao Paulo",
            tipo_incidente="Falha",
            impacto="Alto"
        )
        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["local"] == "Sao Paulo"
