"""Testes unitarios para o servico LLM"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.services.llm_service import OllamaService
from app.models import IncidentResponse


class TestOllamaServiceExtractJson:
    """Testes para o metodo _extract_json"""

    def test_extract_valid_json(self):
        """Deve extrair JSON valido"""
        service = OllamaService()
        text = '{"data_ocorrencia": "2025-02-03 14:00", "local": "Sao Paulo", "tipo_incidente": "Falha", "impacto": "Alto"}'
        result = service._extract_json(text)
        assert result["local"] == "Sao Paulo"

    def test_extract_json_with_markdown(self):
        """Deve extrair JSON mesmo com marcadores markdown"""
        service = OllamaService()
        text = '```json\n{"data_ocorrencia": null, "local": "Rio", "tipo_incidente": "Teste", "impacto": "Baixo"}\n```'
        result = service._extract_json(text)
        assert result["local"] == "Rio"

    def test_extract_json_with_text_before(self):
        """Deve extrair JSON mesmo com texto antes"""
        service = OllamaService()
        text = 'Aqui esta o resultado:\n{"data_ocorrencia": null, "local": "SP", "tipo_incidente": "Erro", "impacto": "Medio"}'
        result = service._extract_json(text)
        assert result["local"] == "SP"

    def test_extract_json_with_text_after(self):
        """Deve extrair JSON mesmo com texto depois"""
        service = OllamaService()
        text = '{"data_ocorrencia": null, "local": "BH", "tipo_incidente": "Bug", "impacto": "Alto"}\nEspero que ajude!'
        result = service._extract_json(text)
        assert result["local"] == "BH"

    def test_extract_json_invalid_raises_exception(self):
        """Deve lancar excecao para JSON invalido"""
        service = OllamaService()
        text = "Resposta sem JSON"
        with pytest.raises(Exception) as exc_info:
            service._extract_json(text)
        assert "JSON valido" in str(exc_info.value)

    def test_extract_json_malformed_raises_exception(self):
        """Deve lancar excecao para JSON malformado"""
        service = OllamaService()
        text = '{"local": "SP", "tipo_incidente": }'
        with pytest.raises(Exception):
            service._extract_json(text)


class TestOllamaServiceConfig:
    """Testes para configuracao do servico"""

    def test_default_config(self):
        """Deve usar configuracao padrao"""
        service = OllamaService()
        assert "11434" in service.base_url
        assert service.timeout == 180.0

    def test_custom_config(self):
        """Deve aceitar configuracao customizada"""
        service = OllamaService(
            base_url="http://custom:1234",
            model="custom-model",
            timeout=60.0
        )
        assert service.base_url == "http://custom:1234"
        assert service.model == "custom-model"
        assert service.timeout == 60.0


class TestOllamaServiceAsync:
    """Testes asincronos para o servico"""

    async def test_health_check_success(self):
        """Deve retornar True quando Ollama esta disponivel"""
        service = OllamaService()
        service.client = AsyncMock()
        service.client.get = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock()
        ))
        
        result = await service.health_check()
        assert result is True

    async def test_health_check_failure(self):
        """Deve retornar False quando Ollama nao esta disponivel"""
        service = OllamaService()
        service.client = AsyncMock()
        service.client.get = AsyncMock(side_effect=Exception("Connection refused"))
        
        result = await service.health_check()
        assert result is False

    async def test_extract_incident_info_success(self):
        """Deve extrair informacoes corretamente"""
        service = OllamaService()
        
        mock_response = {
            "response": '{"data_ocorrencia": "2025-02-03 14:00", "local": "Sao Paulo", "tipo_incidente": "Falha no servidor", "impacto": "Sistema indisponivel"}'
        }
        
        service.client = AsyncMock()
        service.client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))
        
        result = await service.extract_incident_info(
            "Ontem houve falha no servidor de SP",
            "2025-02-04"
        )
        
        assert isinstance(result, IncidentResponse)
        assert result.local == "Sao Paulo"
        assert result.tipo_incidente == "Falha no servidor"

    async def test_close_client(self):
        """Deve fechar cliente HTTP corretamente"""
        service = OllamaService()
        service.client = AsyncMock()
        service.client.aclose = AsyncMock()
        
        await service.close()
        service.client.aclose.assert_called_once()
