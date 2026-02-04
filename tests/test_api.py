"""Testes de integracao para a API"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.models import IncidentResponse
from app.services.llm_service import OllamaService
from app.services.preprocessor import IncidentPreprocessor
from app.exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    JSONParsingError,
    PreprocessingError,
)


@pytest.fixture
def mock_services():
    """Mock dos servicos globais"""
    mock_ollama = MagicMock(spec=OllamaService)
    mock_ollama.health_check = AsyncMock(return_value=True)
    mock_ollama.extract_incident_info = AsyncMock()
    mock_ollama.base_url = "http://ollama:11434"
    mock_ollama.model = "qwen2:0.5b"
    mock_ollama.client = MagicMock()

    mock_preprocessor = MagicMock(spec=IncidentPreprocessor)
    mock_preprocessor.preprocess = MagicMock(
        return_value=("texto processado", "2025-02-04")
    )

    return mock_ollama, mock_preprocessor


@pytest.fixture
def client(mock_services):
    """Cliente de teste com mocks"""
    mock_ollama, mock_preprocessor = mock_services

    with patch("app.main.ollama_service", mock_ollama), patch(
        "app.main.preprocessor", mock_preprocessor
    ):
        yield TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client_simple():
    """Cliente simples sem mocks para testes basicos"""
    return TestClient(app, raise_server_exceptions=False)


class TestRootEndpoint:
    """Testes para o endpoint raiz"""

    def test_root_returns_200(self, client_simple):
        """Deve retornar status 200"""
        response = client_simple.get("/")
        assert response.status_code == 200

    def test_root_returns_service_info(self, client_simple):
        """Deve retornar informacoes do servico"""
        response = client_simple.get("/")
        data = response.json()
        assert data["service"] == "Incident Information Extractor"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "timestamp" in data


class TestHealthEndpoint:
    """Testes para o endpoint de health check"""

    def test_health_returns_200(self, client, mock_services):
        """Deve retornar status 200"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_api_status(self, client, mock_services):
        """Deve retornar status da API"""
        response = client.get("/health")
        data = response.json()
        assert data["api_status"] == "healthy"
        assert "ollama_status" in data
        assert "timestamp" in data

    def test_health_returns_model_info(self, client, mock_services):
        """Deve retornar informacoes do modelo"""
        response = client.get("/health")
        data = response.json()
        assert "ollama_url" in data
        assert "model" in data


class TestExtractIncidentEndpoint:
    """Testes para o endpoint de extracao"""

    def test_extract_requires_body(self, client_simple):
        """Deve rejeitar requisicao sem body"""
        response = client_simple.post("/extract-incident")
        assert response.status_code == 422

    def test_extract_requires_descricao(self, client_simple):
        """Deve rejeitar requisicao sem descricao"""
        response = client_simple.post("/extract-incident", json={})
        assert response.status_code == 422

    def test_extract_validates_min_length(self, client_simple):
        """Deve rejeitar descricao muito curta"""
        response = client_simple.post("/extract-incident", json={"descricao": "curto"})
        assert response.status_code == 422

    def test_extract_accepts_valid_request(self, client, mock_services):
        """Deve aceitar requisicao valida"""
        mock_ollama, _ = mock_services
        mock_ollama.extract_incident_info.return_value = IncidentResponse(
            data_ocorrencia="2025-02-03 14:00",
            local="Sao Paulo",
            tipo_incidente="Falha no servidor",
            impacto="Sistema indisponivel",
        )

        response = client.post(
            "/extract-incident",
            json={"descricao": "Ontem houve uma falha no servidor de Sao Paulo"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["local"] == "Sao Paulo"
        assert data["tipo_incidente"] == "Falha no servidor"


class TestErrorHandlers:
    """Testes para os handlers de erro customizados"""

    def test_llm_connection_error_returns_502(self, client, mock_services):
        """Deve retornar 502 para erro de conexao"""
        mock_ollama, _ = mock_services
        mock_ollama.extract_incident_info.side_effect = LLMConnectionError(
            message="Não foi possível conectar", details="Connection refused"
        )

        response = client.post(
            "/extract-incident",
            json={"descricao": "Descricao de teste para o incidente"},
        )

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "llm_connection_error"
        assert "suggestion" in data

    def test_llm_timeout_error_returns_504(self, client, mock_services):
        """Deve retornar 504 para timeout"""
        mock_ollama, _ = mock_services
        mock_ollama.extract_incident_info.side_effect = LLMTimeoutError(
            message="Timeout", details="180s exceeded"
        )

        response = client.post(
            "/extract-incident",
            json={"descricao": "Descricao de teste para o incidente"},
        )

        assert response.status_code == 504
        data = response.json()
        assert data["error"] == "llm_timeout_error"

    def test_json_parsing_error_returns_422(self, client, mock_services):
        """Deve retornar 422 para erro de parsing JSON"""
        mock_ollama, _ = mock_services
        mock_ollama.extract_incident_info.side_effect = JSONParsingError(
            message="JSON inválido", details="Unexpected token"
        )

        response = client.post(
            "/extract-incident",
            json={"descricao": "Descricao de teste para o incidente"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "json_parsing_error"

    def test_preprocessing_error_returns_400(self, client, mock_services):
        """Deve retornar 400 para erro de preprocessamento"""
        _, mock_preprocessor = mock_services
        mock_preprocessor.preprocess.side_effect = Exception("Encoding error")

        response = client.post(
            "/extract-incident",
            json={"descricao": "Descricao de teste para o incidente"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "preprocessing_error"


class TestModelsEndpoint:
    """Testes para o endpoint de listagem de modelos"""

    def test_models_returns_200_with_mock(self, client, mock_services):
        """Deve retornar lista de modelos"""
        mock_ollama, _ = mock_services
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "qwen2:0.5b"}]}
        mock_response.raise_for_status = MagicMock()
        mock_ollama.client.get = AsyncMock(return_value=mock_response)

        response = client.get("/models")
        assert response.status_code == 200


class TestAPIIntegration:
    """Testes de integracao completa"""

    def test_full_flow_with_mock(self, client, mock_services):
        """Deve processar fluxo completo corretamente"""
        mock_ollama, _ = mock_services
        mock_ollama.extract_incident_info.return_value = IncidentResponse(
            data_ocorrencia="2025-02-03 14:00",
            local="Brasilia",
            tipo_incidente="Queda de energia",
            impacto="Data center afetado",
        )

        # Testa health
        health = client.get("/health")
        assert health.status_code == 200

        # Testa extracao
        extract = client.post(
            "/extract-incident",
            json={
                "descricao": "Ontem houve queda de energia no data center de Brasilia"
            },
        )
        assert extract.status_code == 200
        assert extract.json()["local"] == "Brasilia"
