"""Testes unitarios para os schemas Pydantic"""

import pytest
from pydantic import ValidationError
from app.models import IncidentRequest, IncidentResponse, normalize_date


class TestNormalizeDate:
    """Testes para a funcao normalize_date"""

    def test_valid_format_unchanged(self):
        """Formato correto deve permanecer inalterado"""
        assert normalize_date("2025-02-03 14:00") == "2025-02-03 14:00"

    def test_iso_format_with_seconds(self):
        """Deve converter ISO format com segundos"""
        assert normalize_date("2025-02-03T14:30:00") == "2025-02-03 14:30"

    def test_iso_format_without_seconds(self):
        """Deve converter ISO format sem segundos"""
        assert normalize_date("2025-02-03T14:30") == "2025-02-03 14:30"

    def test_br_format(self):
        """Deve converter formato brasileiro"""
        assert normalize_date("03/02/2025 14:30") == "2025-02-03 14:30"

    def test_br_format_with_seconds(self):
        """Deve converter formato brasileiro com segundos"""
        assert normalize_date("03/02/2025 14:30:45") == "2025-02-03 14:30"

    def test_date_only_adds_midnight(self):
        """Data sem hora deve adicionar 00:00"""
        assert normalize_date("2025-02-03") == "2025-02-03 00:00"

    def test_br_date_only(self):
        """Data brasileira sem hora deve converter"""
        assert normalize_date("03/02/2025") == "2025-02-03 00:00"

    def test_none_returns_none(self):
        """None deve retornar None"""
        assert normalize_date(None) is None

    def test_null_string_returns_none(self):
        """String 'null' deve retornar None"""
        assert normalize_date("null") is None
        assert normalize_date("NULL") is None

    def test_invalid_format_returns_none(self):
        """Formato invalido deve retornar None"""
        assert normalize_date("invalid date") is None
        assert normalize_date("32/13/2025") is None

    def test_empty_string_returns_none(self):
        """String vazia deve retornar None"""
        assert normalize_date("") is None

    def test_whitespace_trimmed(self):
        """Espacos devem ser removidos"""
        assert normalize_date("  2025-02-03 14:00  ") == "2025-02-03 14:00"


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
            impacto="Sistema indisponivel",
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
            impacto="Dados comprometidos",
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
            impacto="Alto",
        )
        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["local"] == "Sao Paulo"

    def test_date_normalization_iso_format(self):
        """Deve normalizar data em formato ISO"""
        response = IncidentResponse(data_ocorrencia="2025-02-03T14:30:00")
        assert response.data_ocorrencia == "2025-02-03 14:30"

    def test_date_normalization_br_format(self):
        """Deve normalizar data em formato brasileiro"""
        response = IncidentResponse(data_ocorrencia="03/02/2025 14:30")
        assert response.data_ocorrencia == "2025-02-03 14:30"

    def test_date_normalization_invalid_returns_none(self):
        """Deve retornar None para data invalida"""
        response = IncidentResponse(data_ocorrencia="data invalida")
        assert response.data_ocorrencia is None

    def test_date_normalization_null_string(self):
        """Deve converter string 'null' para None"""
        response = IncidentResponse(data_ocorrencia="null")
        assert response.data_ocorrencia is None
