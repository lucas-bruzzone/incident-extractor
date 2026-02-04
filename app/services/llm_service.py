"""Servico de integracao com Ollama LLM"""

import httpx
import json
import logging
import os
import asyncio
from typing import Dict
from app.models import IncidentResponse
from app.prompts import build_extraction_prompt
from app.exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    LLMResponseError,
    JSONParsingError,
)

logger = logging.getLogger(__name__)


class OllamaService:
    """Cliente para comunicacao com API Ollama"""

    def __init__(self, base_url: str = None, model: str = None, timeout: float = 180.0):
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.model = model or os.getenv("OLLAMA_MODEL", "tinyllama")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(
            f"OllamaService inicializado: {self.base_url} | Modelo: {self.model}"
        )

    async def extract_incident_info(
        self, incident_description: str, reference_date: str
    ) -> IncidentResponse:
        """
        Extrai informacoes estruturadas de um incidente usando LLM

        Raises:
            LLMConnectionError: Falha de conexão com Ollama
            LLMTimeoutError: Timeout na requisição
            JSONParsingError: Resposta não contém JSON válido
            LLMResponseError: Outros erros de resposta do LLM
        """
        prompt = build_extraction_prompt(incident_description, reference_date)

        logger.info(f"Enviando requisicao para Ollama (modelo: {self.model})")

        response = await self._generate_with_retry(prompt)

        json_data = self._extract_json(response)

        incident_data = IncidentResponse(**json_data)

        logger.info("Extracao concluida com sucesso")
        return incident_data

    async def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """
        Envia prompt para o modelo Ollama com retry

        Raises:
            LLMConnectionError: Após todas tentativas falharem por conexão
            LLMTimeoutError: Após todas tentativas falharem por timeout
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await self._generate(prompt)
            except LLMTimeoutError:
                raise  # Não faz retry em timeout
            except LLMConnectionError as e:
                last_error = e
                wait_time = 2**attempt
                logger.warning(
                    f"Tentativa {attempt + 1}/{max_retries} falhou: {e.message}. "
                    f"Aguardando {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = LLMResponseError(
                    message="Erro inesperado na comunicação com LLM", details=str(e)
                )
                wait_time = 2**attempt
                logger.warning(
                    f"Tentativa {attempt + 1}/{max_retries} falhou: {str(e)}. "
                    f"Aguardando {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

        if isinstance(last_error, LLMConnectionError):
            raise last_error
        raise LLMConnectionError(
            message="Falha ao conectar com Ollama após múltiplas tentativas",
            details=str(last_error) if last_error else None,
        )

    async def _generate(self, prompt: str) -> str:
        """
        Envia prompt para o modelo Ollama

        Raises:
            LLMConnectionError: Erro de conexão
            LLMTimeoutError: Timeout na requisição
            LLMResponseError: Erro HTTP do servidor
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "top_p": 0.9},
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except httpx.TimeoutException as e:
            logger.error(f"Timeout ao chamar Ollama: {str(e)}")
            raise LLMTimeoutError(
                message="Tempo limite excedido aguardando resposta do LLM",
                details=f"Timeout após {self.timeout}s",
            )
        except httpx.ConnectError as e:
            logger.error(f"Erro de conexao com Ollama: {str(e)}")
            raise LLMConnectionError(
                message="Não foi possível conectar ao serviço Ollama",
                details=f"Verifique se o Ollama está rodando em {self.base_url}",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP ao chamar Ollama: {e.response.status_code}")
            raise LLMResponseError(
                message=f"Ollama retornou erro HTTP {e.response.status_code}",
                details=e.response.text[:500] if e.response.text else None,
            )
        except httpx.RequestError as e:
            logger.error(f"Erro de requisicao com Ollama: {str(e)}")
            raise LLMConnectionError(
                message="Erro na requisição ao Ollama", details=str(e)
            )

    def _extract_json(self, text: str) -> Dict:
        """
        Extrai JSON da resposta do LLM

        Raises:
            JSONParsingError: Se não conseguir extrair JSON válido
        """
        logger.info(f"Resposta do LLM (primeiros 500 chars): {text[:500]}")

        text = text.strip()
        text = text.replace("```json", "").replace("```", "")
        text = text.strip()

        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx == -1 or end_idx == -1:
            logger.error(f"Nao ha chaves na resposta: {text[:200]}")
            raise JSONParsingError(
                message="Resposta do LLM não contém JSON",
                details=f"Resposta recebida: {text[:200]}...",
            )

        json_str = text[start_idx : end_idx + 1]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {str(e)}")
            logger.error(f"JSON problematico: {json_str}")

            # Tenta corrigir quebras de linha dentro de strings
            import re

            json_str_fixed = re.sub(r'"\s*\n\s*', '" ', json_str)

            try:
                return json.loads(json_str_fixed)
            except json.JSONDecodeError:
                raise JSONParsingError(
                    message="JSON malformado na resposta do LLM",
                    details=f"Erro: {str(e)}. JSON: {json_str[:200]}...",
                )

    async def health_check(self) -> bool:
        """
        Verifica se o servico Ollama esta disponivel
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = await self.client.get(url)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Health check falhou: {str(e)}")
            return False

    async def close(self):
        """Fecha a conexao HTTP"""
        await self.client.aclose()
