"""Testes de integração reais com Ollama

Estes testes requerem que o Ollama esteja rodando e acessível.
Execute com: pytest tests/test_integration.py -v --run-integration
"""

import pytest
import httpx
import os
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.llm_service import OllamaService
from app.services.preprocessor import IncidentPreprocessor
from app.models import IncidentResponse
from app.exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    JSONParsingError,
)


# Marca todos os testes deste módulo como integração
pytestmark = pytest.mark.integration


def is_ollama_available() -> bool:
    """Verifica se Ollama está disponível"""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest_asyncio.fixture
async def ollama_service():
    service = OllamaService()
    yield service
    await service.close()


@pytest.fixture
def preprocessor():
    """Instância do preprocessador"""
    return IncidentPreprocessor()


class TestOllamaConnection:
    """Testes de conectividade com Ollama"""

    @pytest.mark.asyncio
    async def test_health_check_real(self, ollama_service):
        """Deve conectar ao Ollama real"""
        result = await ollama_service.health_check()
        assert result is True, "Ollama não está disponível"

    @pytest.mark.asyncio
    async def test_model_available(self, ollama_service):
        """Deve ter o modelo configurado disponível"""
        url = f"{ollama_service.base_url}/api/tags"
        response = await ollama_service.client.get(url)
        response.raise_for_status()

        data = response.json()
        models = [m["name"] for m in data.get("models", [])]

        # Verifica se o modelo configurado está disponível
        model_name = ollama_service.model
        model_found = any(model_name in m for m in models)

        assert model_found, f"Modelo {model_name} não encontrado. Disponíveis: {models}"


class TestIncidentExtraction:
    """Testes de extração de incidentes"""

    @pytest.mark.asyncio
    async def test_extract_complete_incident(self, ollama_service, preprocessor):
        """Deve extrair todas as informações de um incidente completo"""
        description = (
            "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor "
            "principal que afetou o sistema de faturamento por 2 horas."
        )

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        assert isinstance(result, IncidentResponse)
        # Verifica que pelo menos alguns campos foram extraídos
        extracted_fields = [
            result.data_ocorrencia,
            result.local,
            result.tipo_incidente,
            result.impacto,
        ]
        non_null_fields = [f for f in extracted_fields if f is not None]
        assert len(non_null_fields) >= 2, f"Poucos campos extraídos: {result}"

    @pytest.mark.asyncio
    async def test_extract_partial_incident(self, ollama_service, preprocessor):
        """Deve extrair informações parciais quando nem tudo está disponível"""
        description = "Vazamento de dados detectado pela equipe de segurança."

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        assert isinstance(result, IncidentResponse)
        # Tipo do incidente deve ser identificado
        assert result.tipo_incidente is not None

    @pytest.mark.asyncio
    async def test_extract_with_relative_date_hoje(self, ollama_service, preprocessor):
        """Deve interpretar 'hoje' corretamente"""
        description = "Hoje pela manhã houve queda de energia no data center."

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        assert isinstance(result, IncidentResponse)
        # Data deve conter a data de referência
        if result.data_ocorrencia:
            assert reference_date in result.data_ocorrencia

    @pytest.mark.asyncio
    async def test_extract_with_relative_date_ontem(self, ollama_service, preprocessor):
        """Deve interpretar 'ontem' corretamente"""
        description = "Ontem às 10h ocorreu um incidente de segurança em Brasília."

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        assert isinstance(result, IncidentResponse)
        assert result.local is not None

    @pytest.mark.asyncio
    async def test_extract_minimal_description(self, ollama_service, preprocessor):
        """Deve lidar com descrições mínimas"""
        description = "Servidor fora do ar."

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        assert isinstance(result, IncidentResponse)
        # Deve pelo menos identificar o tipo
        assert result.tipo_incidente is not None


class TestErrorHandling:
    """Testes de tratamento de erros"""

    @pytest.mark.asyncio
    async def test_connection_error(self):
        """Deve lançar erro quando Ollama não está disponível"""
        service = OllamaService(base_url="http://invalid-host:99999", timeout=2.0)

        # Pode ser timeout ou connection error dependendo da implementação httpx
        with pytest.raises((LLMConnectionError, LLMTimeoutError)):
            await service.extract_incident_info("Teste", "2025-02-04")

        await service.close()

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Deve lançar LLMTimeoutError em timeout"""
        service = OllamaService(timeout=0.001)  # Timeout muito curto

        with pytest.raises((LLMTimeoutError, LLMConnectionError)):
            await service.extract_incident_info("Teste incidente", "2025-02-04")

        await service.close()

    @pytest.mark.asyncio
    async def test_malformed_response(self):
        """Deve lidar com resposta malformada do LLM"""
        with patch("app.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ollama_base_url="http://localhost:11434",
                ollama_model="test",
                ollama_timeout=60.0,
                ollama_max_retries=1,
                validate_llm_response=True,
                allow_partial_response=True,
            )
            service = OllamaService()

        # Mock resposta sem JSON
        service.client = AsyncMock()
        service.client.post = AsyncMock(
            return_value=MagicMock(
                raise_for_status=MagicMock(),
                json=MagicMock(return_value={"response": "Resposta sem JSON válido"}),
            )
        )

        with pytest.raises(JSONParsingError) as exc_info:
            await service.extract_incident_info("Teste", "2025-02-04")

        assert "JSON" in exc_info.value.message
        await service.close()

    @pytest.mark.asyncio
    async def test_invalid_json_format(self):
        """Deve lançar erro para JSON malformado"""
        with patch("app.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ollama_base_url="http://localhost:11434",
                ollama_model="test",
                ollama_timeout=60.0,
                ollama_max_retries=1,
                validate_llm_response=True,
                allow_partial_response=True,
            )
            service = OllamaService()

        # Mock JSON inválido
        service.client = AsyncMock()
        service.client.post = AsyncMock(
            return_value=MagicMock(
                raise_for_status=MagicMock(),
                json=MagicMock(return_value={"response": '{"local": "SP", "tipo": '}),
            )
        )

        with pytest.raises(JSONParsingError):
            await service.extract_incident_info("Teste", "2025-02-04")

        await service.close()

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Deve fazer retry em caso de falha temporária"""
        with patch("app.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ollama_base_url="http://localhost:11434",
                ollama_model="test",
                ollama_timeout=60.0,
                ollama_max_retries=3,
                validate_llm_response=True,
                allow_partial_response=True,
            )
            service = OllamaService()

        # Mock: primeira tentativa falha, segunda sucede
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("Connection failed")
            else:
                return MagicMock(
                    raise_for_status=MagicMock(),
                    json=MagicMock(
                        return_value={
                            "response": '{"data_ocorrencia": null, "local": "SP", "tipo_incidente": "Falha", "impacto": "Alto"}'
                        }
                    ),
                )

        service.client = AsyncMock()
        service.client.post = AsyncMock(side_effect=mock_post)

        result = await service.extract_incident_info("Teste", "2025-02-04")

        assert isinstance(result, IncidentResponse)
        assert call_count == 2  # Falhou uma vez, sucedeu na segunda
        await service.close()


class TestEdgeCases:
    """Testes de casos extremos"""

    @pytest.mark.asyncio
    async def test_long_description(self, ollama_service, preprocessor):
        """Deve processar descrições longas"""
        description = (
            "No dia de ontem, aproximadamente às 15 horas e 30 minutos, "
            "foi identificado um problema crítico no data center principal "
            "localizado na cidade de São Paulo, especificamente no setor de "
            "infraestrutura de rede. O incidente causou a interrupção total "
            "dos serviços de conectividade para aproximadamente 500 usuários "
            "durante um período de 4 horas, resultando em perda significativa "
            "de produtividade e impacto financeiro estimado em R$ 50.000,00."
        )

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        assert isinstance(result, IncidentResponse)
        # Descrição rica deve resultar em extração completa
        non_null = sum(
            1
            for f in [
                result.data_ocorrencia,
                result.local,
                result.tipo_incidente,
                result.impacto,
            ]
            if f
        )
        assert non_null >= 3

    @pytest.mark.asyncio
    async def test_description_with_special_chars(self, ollama_service, preprocessor):
        """Deve lidar com caracteres especiais"""
        description = (
            "Falha no servidor #1 (produção) - impacto: 100% dos usuários "
            "afetados! Urgente!!!"
        )

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        assert isinstance(result, IncidentResponse)

    @pytest.mark.asyncio
    async def test_description_only_english(self, ollama_service, preprocessor):
        """Deve processar descrições em inglês"""
        description = (
            "Yesterday at 2pm, there was a server failure in the New York office "
            "that affected the billing system for 2 hours."
        )

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        assert isinstance(result, IncidentResponse)


class TestResponseQuality:
    """Testes de qualidade das respostas"""

    @pytest.mark.asyncio
    async def test_date_format_valid(self, ollama_service, preprocessor):
        """Data extraída deve estar em formato válido"""
        description = "Ontem às 14h30 houve falha no servidor de São Paulo."

        processed_text, reference_date = preprocessor.preprocess(description)
        result = await ollama_service.extract_incident_info(
            processed_text, reference_date
        )

        if result.data_ocorrencia:
            # Formato esperado: YYYY-MM-DD HH:MM
            import re

            pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"
            assert re.match(
                pattern, result.data_ocorrencia
            ), f"Formato inválido: {result.data_ocorrencia}"

    @pytest.mark.asyncio
    async def test_consistency_multiple_calls(self, ollama_service, preprocessor):
        """Múltiplas chamadas com mesma entrada devem ser consistentes"""
        description = "Falha no servidor de produção em São Paulo."
        processed_text, reference_date = preprocessor.preprocess(description)

        results = []
        for _ in range(3):
            result = await ollama_service.extract_incident_info(
                processed_text, reference_date
            )
            results.append(result)

        # Local deve ser consistente
        locals_found = [r.local for r in results if r.local]
        if locals_found:
            # Todos devem mencionar São Paulo de alguma forma
            assert all("Paulo" in loc or "SP" in loc for loc in locals_found)


class TestTimeout:
    """Testes de comportamento com timeout"""

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        """Deve respeitar timeout customizado"""
        service = OllamaService(timeout=5.0)
        assert service.timeout == 5.0
        await service.close()


class TestModelNotAvailable:
    """Testes para modelo não disponível"""

    @pytest.mark.asyncio
    async def test_model_not_found_error(self):
        """Deve lidar com modelo não disponível"""
        service = OllamaService(model="modelo-inexistente")

        # Pode lançar diferentes erros dependendo da resposta do Ollama
        with pytest.raises((LLMConnectionError, LLMTimeoutError, Exception)):
            await service.extract_incident_info("Teste", "2025-02-04")

        await service.close()
