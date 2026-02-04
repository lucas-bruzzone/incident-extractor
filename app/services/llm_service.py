"""Servico de integracao com Ollama LLM"""

import httpx
import json
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
from app.logging_config import get_logger

logger = get_logger(__name__)


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
            "OllamaService inicializado",
            extra={"base_url": self.base_url, "model": self.model},
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

        logger.info(
            "Enviando requisicao para Ollama",
            extra={"model": self.model, "prompt_length": len(prompt)},
        )

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
                    "Tentativa falhou, aguardando retry",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "wait_time": wait_time,
                        "error": e.message,
                    },
                )
                await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = LLMResponseError(
                    message="Erro inesperado na comunicação com LLM", details=str(e)
                )
                wait_time = 2**attempt
                logger.warning(
                    "Tentativa falhou com erro inesperado",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "wait_time": wait_time,
                        "error": str(e),
                    },
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
            logger.error("Timeout ao chamar Ollama", extra={"error": str(e)})
            raise LLMTimeoutError(
                message="Tempo limite excedido aguardando resposta do LLM",
                details=f"Timeout após {self.timeout}s",
            )
        except httpx.ConnectError as e:
            logger.error("Erro de conexao com Ollama", extra={"error": str(e)})
            raise LLMConnectionError(
                message="Não foi possível conectar ao serviço Ollama",
                details=f"Verifique se o Ollama está rodando em {self.base_url}",
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Erro HTTP ao chamar Ollama",
                extra={"status_code": e.response.status_code},
            )
            raise LLMResponseError(
                message=f"Ollama retornou erro HTTP {e.response.status_code}",
                details=e.response.text[:500] if e.response.text else None,
            )
        except httpx.RequestError as e:
            logger.error("Erro de requisicao com Ollama", extra={"error": str(e)})
            raise LLMConnectionError(
                message="Erro na requisição ao Ollama", details=str(e)
            )

    def _extract_json(self, text: str) -> Dict:
        logger.info(
            "Processando resposta do LLM",
            extra={"response_preview": text[:200] if text else "empty"},
        )

        if not text:
            raise JSONParsingError(
                message="Resposta vazia do LLM",
                details="Nenhum conteúdo retornado",
            )

        # Remove blocos markdown
        cleaned = text.replace("```json", "").replace("```", "").strip()

        # Tenta localizar início do JSON
        start_idx = cleaned.find("{")
        if start_idx == -1:
            raise JSONParsingError(
                message="Resposta do LLM não contém JSON",
                details=cleaned[:200],
            )

        candidate = cleaned[start_idx:]

        # 🔧 CASO CRÍTICO: JSON truncado (faltando })
        open_braces = candidate.count("{")
        close_braces = candidate.count("}")

        if close_braces < open_braces:
            candidate = candidate + ("}" * (open_braces - close_braces))

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            logger.error(
                "Erro ao parsear JSON",
                extra={
                    "error": str(e),
                    "json_preview": candidate[:200],
                },
            )
            raise JSONParsingError(
                message="JSON malformado na resposta do LLM",
                details=str(e),
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
            logger.error("Health check falhou", extra={"error": str(e)})
            return False

    async def close(self):
        """Fecha a conexao HTTP"""
        await self.client.aclose()
