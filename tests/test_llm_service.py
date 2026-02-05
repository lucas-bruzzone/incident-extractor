"""Testes unitarios para o servico LLM"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.llm_service import OllamaService, ResponseValidator, EXPECTED_FIELDS
from app.models import IncidentResponse
from app.exceptions import LLMConnectionError, LLMTimeoutError, JSONParsingError


class TestResponseValidator:
    """Testes para o validador de schema"""

    def test_validate_complete_response(self):
        """Deve aceitar resposta completa"""
        validator = ResponseValidator(allow_partial=True)
        data = {
            "data_ocorrencia": "2025-02-03 14:00",
            "local": "Sao Paulo",
            "tipo_incidente": "Falha",
            "impacto": "Alto",
        }
        result = validator.validate(data)
        assert result["local"] == "Sao Paulo"
        assert result["tipo_incidente"] == "Falha"

    def test_validate_partial_response_allowed(self):
        """Deve preencher campos faltando com null quando permitido"""
        validator = ResponseValidator(allow_partial=True)
        data = {
            "tipo_incidente": "Falha",
            "impacto": "Alto",
        }
        result = validator.validate(data)
        assert result["data_ocorrencia"] is None
        assert result["local"] is None
        assert result["tipo_incidente"] == "Falha"

    def test_validate_partial_response_not_allowed(self):
        """Deve rejeitar resposta parcial quando não permitido"""
        validator = ResponseValidator(allow_partial=False)
        data = {
            "tipo_incidente": "Falha",
            "impacto": "Alto",
        }
        with pytest.raises(JSONParsingError) as exc_info:
            validator.validate(data)
        assert "faltando" in exc_info.value.message.lower()

    def test_validate_ignores_unknown_fields(self):
        """Deve ignorar campos desconhecidos"""
        validator = ResponseValidator(allow_partial=True)
        data = {
            "data_ocorrencia": "2025-02-03 14:00",
            "local": "Sao Paulo",
            "tipo_incidente": "Falha",
            "impacto": "Alto",
            "campo_extra": "valor",
        }
        result = validator.validate(data)
        assert "campo_extra" not in result
        assert len(result) == 4

    def test_validate_normalizes_null_strings(self):
        """Deve normalizar strings 'null' para None"""
        validator = ResponseValidator(allow_partial=True)
        data = {
            "data_ocorrencia": "null",
            "local": "NULL",
            "tipo_incidente": "none",
            "impacto": "N/A",
        }
        result = validator.validate(data)
        assert result["data_ocorrencia"] is None
        assert result["local"] is None
        assert result["tipo_incidente"] is None
        assert result["impacto"] is None

    def test_validate_trims_whitespace(self):
        """Deve remover espaços em branco"""
        validator = ResponseValidator(allow_partial=True)
        data = {
            "data_ocorrencia": "  2025-02-03 14:00  ",
            "local": "  Sao Paulo  ",
            "tipo_incidente": "  Falha  ",
            "impacto": "  Alto  ",
        }
        result = validator.validate(data)
        assert result["data_ocorrencia"] == "2025-02-03 14:00"
        assert result["local"] == "Sao Paulo"

    def test_validate_converts_non_strings(self):
        """Deve converter valores não-string para string"""
        validator = ResponseValidator(allow_partial=True)
        data = {
            "data_ocorrencia": None,
            "local": 123,
            "tipo_incidente": True,
            "impacto": ["lista"],
        }
        result = validator.validate(data)
        assert result["data_ocorrencia"] is None
        assert result["local"] == "123"

    def test_validate_rejects_non_dict(self):
        """Deve rejeitar entrada que não é dicionário"""
        validator = ResponseValidator(allow_partial=True)

        with pytest.raises(JSONParsingError) as exc_info:
            validator.validate("string")
        assert "não é um objeto" in exc_info.value.message.lower()

        with pytest.raises(JSONParsingError):
            validator.validate([1, 2, 3])

    def test_validate_empty_strings_become_none(self):
        """Strings vazias devem virar None"""
        validator = ResponseValidator(allow_partial=True)
        data = {
            "data_ocorrencia": "",
            "local": "   ",
            "tipo_incidente": "-",
            "impacto": "na",
        }
        result = validator.validate(data)
        assert result["data_ocorrencia"] is None
        assert result["local"] is None
        assert result["tipo_incidente"] is None
        assert result["impacto"] is None


class TestOllamaServiceExtractJson:
    """Testes para o metodo _extract_json"""

    def test_extract_valid_json(self):
        """Deve extrair JSON valido"""
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

        text = '{"data_ocorrencia": "2025-02-03 14:00", "local": "Sao Paulo", "tipo_incidente": "Falha", "impacto": "Alto"}'
        result = service._extract_json(text)
        assert result["local"] == "Sao Paulo"

    def test_extract_json_with_markdown(self):
        """Deve extrair JSON mesmo com marcadores markdown"""
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

        text = '```json\n{"data_ocorrencia": null, "local": "Rio", "tipo_incidente": "Teste", "impacto": "Baixo"}\n```'
        result = service._extract_json(text)
        assert result["local"] == "Rio"

    def test_extract_json_with_text_before(self):
        """Deve extrair JSON mesmo com texto antes"""
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

        text = 'Aqui esta o resultado:\n{"data_ocorrencia": null, "local": "SP", "tipo_incidente": "Erro", "impacto": "Medio"}'
        result = service._extract_json(text)
        assert result["local"] == "SP"

    def test_extract_json_with_text_after(self):
        """Deve extrair JSON mesmo com texto depois"""
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

        text = '{"data_ocorrencia": null, "local": "BH", "tipo_incidente": "Bug", "impacto": "Alto"}\nEspero que ajude!'
        result = service._extract_json(text)
        assert result["local"] == "BH"

    def test_extract_json_no_braces_raises_json_parsing_error(self):
        """Deve lancar JSONParsingError para resposta sem chaves"""
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

        text = "Resposta sem JSON"
        with pytest.raises(JSONParsingError) as exc_info:
            service._extract_json(text)
        assert "JSON" in exc_info.value.message

    def test_extract_json_malformed_raises_json_parsing_error(self):
        """Deve lancar JSONParsingError para JSON malformado"""
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

        text = '{"local": "SP", "tipo_incidente": }'
        with pytest.raises(JSONParsingError):
            service._extract_json(text)


class TestOllamaServiceConfig:
    """Testes para configuracao do servico"""

    def test_default_config(self):
        """Deve usar configuracao padrao do settings"""
        with patch("app.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ollama_base_url="http://localhost:11434",
                ollama_model="qwen2:0.5b",
                ollama_timeout=180.0,
                ollama_max_retries=3,
                validate_llm_response=True,
                allow_partial_response=True,
            )
            service = OllamaService()

        assert service.base_url == "http://localhost:11434"
        assert service.model == "qwen2:0.5b"
        assert service.timeout == 180.0

    def test_custom_config_overrides_settings(self):
        """Deve aceitar configuracao customizada que sobrescreve settings"""
        with patch("app.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ollama_base_url="http://default:11434",
                ollama_model="default-model",
                ollama_timeout=180.0,
                ollama_max_retries=3,
                validate_llm_response=True,
                allow_partial_response=True,
            )
            service = OllamaService(
                base_url="http://custom:1234", model="custom-model", timeout=60.0
            )

        assert service.base_url == "http://custom:1234"
        assert service.model == "custom-model"
        assert service.timeout == 60.0


class TestOllamaServiceAsync:
    """Testes asincronos para o servico"""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Deve retornar True quando Ollama esta disponivel"""
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

        service.client = AsyncMock()
        service.client.get = AsyncMock(
            return_value=MagicMock(raise_for_status=MagicMock())
        )

        result = await service.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Deve retornar False quando Ollama nao esta disponivel"""
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

        service.client = AsyncMock()
        service.client.get = AsyncMock(side_effect=Exception("Connection refused"))

        result = await service.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_extract_incident_info_success(self):
        """Deve extrair informacoes corretamente"""
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

        mock_response = {
            "response": '{"data_ocorrencia": "2025-02-03 14:00", "local": "Sao Paulo", "tipo_incidente": "Falha no servidor", "impacto": "Sistema indisponivel"}'
        }

        service.client = AsyncMock()
        service.client.post = AsyncMock(
            return_value=MagicMock(
                raise_for_status=MagicMock(), json=MagicMock(return_value=mock_response)
            )
        )

        result = await service.extract_incident_info(
            "Ontem houve falha no servidor de SP", "2025-02-04"
        )

        assert isinstance(result, IncidentResponse)
        assert result.local == "Sao Paulo"
        assert result.tipo_incidente == "Falha no servidor"

    @pytest.mark.asyncio
    async def test_extract_incident_info_with_validation(self):
        """Deve validar schema da resposta"""
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

        # Resposta parcial (falta data_ocorrencia e local)
        mock_response = {"response": '{"tipo_incidente": "Falha", "impacto": "Alto"}'}

        service.client = AsyncMock()
        service.client.post = AsyncMock(
            return_value=MagicMock(
                raise_for_status=MagicMock(), json=MagicMock(return_value=mock_response)
            )
        )

        result = await service.extract_incident_info("Incidente teste", "2025-02-04")

        assert isinstance(result, IncidentResponse)
        assert result.data_ocorrencia is None  # Preenchido com None
        assert result.local is None  # Preenchido com None
        assert result.tipo_incidente == "Falha"

    @pytest.mark.asyncio
    async def test_generate_timeout_raises_llm_timeout_error(self):
        """Deve lancar LLMTimeoutError em timeout"""
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

        service.client = AsyncMock()
        service.client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(LLMTimeoutError):
            await service._generate("test prompt")

    @pytest.mark.asyncio
    async def test_generate_connection_error_raises_llm_connection_error(self):
        """Deve lancar LLMConnectionError em erro de conexao"""
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

        service.client = AsyncMock()
        service.client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with pytest.raises(LLMConnectionError):
            await service._generate("test prompt")

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Deve fechar cliente HTTP corretamente"""
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

        service.client = AsyncMock()
        service.client.aclose = AsyncMock()

        await service.close()
        service.client.aclose.assert_called_once()


class TestExpectedFields:
    """Testes para campos esperados"""

    def test_expected_fields_contains_all_fields(self):
        """Deve conter todos os campos do schema"""
        assert "data_ocorrencia" in EXPECTED_FIELDS
        assert "local" in EXPECTED_FIELDS
        assert "tipo_incidente" in EXPECTED_FIELDS
        assert "impacto" in EXPECTED_FIELDS
        assert len(EXPECTED_FIELDS) == 4
