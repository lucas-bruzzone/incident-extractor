"""Testes de integração reais com Ollama

Estes testes requerem que o Ollama esteja rodando e acessível.
Execute com: pytest tests/test_integration.py -v --run-integration
"""

import pytest
import httpx
import os
import pytest_asyncio

from app.services.llm_service import OllamaService
from app.services.preprocessor import IncidentPreprocessor
from app.models import IncidentResponse


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
