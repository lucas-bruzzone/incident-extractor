"""Testes de integracao para a API"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.models import IncidentResponse
from app.services.llm_service import OllamaService
from app.services.preprocessor import IncidentPreprocessor


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

    def test_health_returns_200(self):
        """Deve retornar status 200"""
        mock_ollama = MagicMock(spec=OllamaService)
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_ollama.base_url = "http://ollama:11434"
        mock_ollama.model = "qwen2:0.5b"

        mock_preprocessor = MagicMock(spec=IncidentPreprocessor)

        with patch("app.main.ollama_service", mock_ollama), patch(
            "app.main.preprocessor", mock_preprocessor
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_api_status(self):
        """Deve retornar status da API"""
        mock_ollama = MagicMock(spec=OllamaService)
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_ollama.base_url = "http://ollama:11434"
        mock_ollama.model = "qwen2:0.5b"

        mock_preprocessor = MagicMock(spec=IncidentPreprocessor)

        with patch("app.main.ollama_service", mock_ollama), patch(
            "app.main.preprocessor", mock_preprocessor
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/health")

        data = response.json()
        assert data["api_status"] == "healthy"
        assert "ollama_status" in data
        assert "timestamp" in data

    def test_health_returns_model_info(self):
        """Deve retornar informacoes do modelo"""
        mock_ollama = MagicMock(spec=OllamaService)
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_ollama.base_url = "http://ollama:11434"
        mock_ollama.model = "qwen2:0.5b"

        mock_preprocessor = MagicMock(spec=IncidentPreprocessor)

        with patch("app.main.ollama_service", mock_ollama), patch(
            "app.main.preprocessor", mock_preprocessor
        ):
            client = TestClient(app, raise_server_exceptions=False)
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

    def test_extract_accepts_valid_request(self):
        """Deve aceitar requisicao valida"""
        mock_ollama = MagicMock(spec=OllamaService)
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_ollama.extract_incident_info = AsyncMock(
            return_value=IncidentResponse(
                data_ocorrencia="2025-02-03 14:00",
                local="Sao Paulo",
                tipo_incidente="Falha no servidor",
                impacto="Sistema indisponivel",
            )
        )
        mock_ollama.base_url = "http://ollama:11434"
        mock_ollama.model = "qwen2:0.5b"

        mock_preprocessor = MagicMock(spec=IncidentPreprocessor)
        mock_preprocessor.preprocess = MagicMock(
            return_value=("texto processado", "2025-02-04")
        )

        with patch("app.main.ollama_service", mock_ollama), patch(
            "app.main.preprocessor", mock_preprocessor
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/extract-incident",
                json={"descricao": "Ontem houve uma falha no servidor de Sao Paulo"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["local"] == "Sao Paulo"
        assert data["tipo_incidente"] == "Falha no servidor"


class TestModelsEndpoint:
    """Testes para o endpoint de listagem de modelos"""

    def test_models_returns_200_with_mock(self):
        """Deve retornar lista de modelos"""
        mock_ollama = MagicMock(spec=OllamaService)
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_ollama.base_url = "http://ollama:11434"
        mock_ollama.model = "qwen2:0.5b"

        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "qwen2:0.5b"}]}
        mock_response.raise_for_status = MagicMock()
        mock_ollama.client = MagicMock()
        mock_ollama.client.get = AsyncMock(return_value=mock_response)

        mock_preprocessor = MagicMock(spec=IncidentPreprocessor)

        with patch("app.main.ollama_service", mock_ollama), patch(
            "app.main.preprocessor", mock_preprocessor
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/models")

        assert response.status_code == 200


class TestAPIIntegration:
    """Testes de integracao completa"""

    def test_full_flow_with_mock(self):
        """Deve processar fluxo completo corretamente"""
        mock_ollama = MagicMock(spec=OllamaService)
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_ollama.extract_incident_info = AsyncMock(
            return_value=IncidentResponse(
                data_ocorrencia="2025-02-03 14:00",
                local="Brasilia",
                tipo_incidente="Queda de energia",
                impacto="Data center afetado",
            )
        )
        mock_ollama.base_url = "http://ollama:11434"
        mock_ollama.model = "qwen2:0.5b"

        mock_preprocessor = MagicMock(spec=IncidentPreprocessor)
        mock_preprocessor.preprocess = MagicMock(
            return_value=("texto processado", "2025-02-04")
        )

        with patch("app.main.ollama_service", mock_ollama), patch(
            "app.main.preprocessor", mock_preprocessor
        ):
            client = TestClient(app, raise_server_exceptions=False)

            health = client.get("/health")
            assert health.status_code == 200

            extract = client.post(
                "/extract-incident",
                json={
                    "descricao": "Ontem houve queda de energia no data center de Brasilia"
                },
            )
            assert extract.status_code == 200
            assert extract.json()["local"] == "Brasilia"


class TestRequestTracing:
    """Testes para rastreamento de requests"""

    def test_request_has_request_id_header(self):
        """Deve incluir X-Request-ID na resposta"""
        mock_ollama = MagicMock(spec=OllamaService)
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_ollama.base_url = "http://ollama:11434"
        mock_ollama.model = "qwen2:0.5b"

        mock_preprocessor = MagicMock(spec=IncidentPreprocessor)

        with patch("app.main.ollama_service", mock_ollama), patch(
            "app.main.preprocessor", mock_preprocessor
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/health")

        assert "X-Request-ID" in response.headers

    def test_custom_request_id_is_preserved(self):
        """Deve preservar X-Request-ID customizado"""
        mock_ollama = MagicMock(spec=OllamaService)
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_ollama.base_url = "http://ollama:11434"
        mock_ollama.model = "qwen2:0.5b"

        mock_preprocessor = MagicMock(spec=IncidentPreprocessor)

        with patch("app.main.ollama_service", mock_ollama), patch(
            "app.main.preprocessor", mock_preprocessor
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/health", headers={"X-Request-ID": "custom-id-123"})

        assert response.headers["X-Request-ID"] == "custom-id-123"
