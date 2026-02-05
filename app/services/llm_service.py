"""Servico de integracao com Ollama LLM"""

import httpx
import json
import asyncio
import re
from typing import Dict, Any, Optional
from app.models import IncidentResponse
from app.prompts import build_extraction_prompt
from app.config import get_settings
from app.exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    LLMResponseError,
    JSONParsingError,
)
from app.logging_config import get_logger

logger = get_logger(__name__)

# Campos esperados na resposta do LLM
EXPECTED_FIELDS = {"data_ocorrencia", "local", "tipo_incidente", "impacto"}


class ResponseValidator:
    """Validador de schema para respostas do LLM"""

    def __init__(self, allow_partial: bool = True):
        """
        Args:
            allow_partial: Se True, permite campos faltando (serão null)
        """
        self.allow_partial = allow_partial

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida e normaliza a resposta do LLM.

        Args:
            data: Dicionário parseado do JSON

        Returns:
            Dicionário validado e normalizado

        Raises:
            JSONParsingError: Se validação falhar
        """
        if not isinstance(data, dict):
            raise JSONParsingError(
                message="Resposta do LLM não é um objeto JSON",
                details=f"Tipo recebido: {type(data).__name__}",
            )

        # Verificar campos desconhecidos
        unknown_fields = set(data.keys()) - EXPECTED_FIELDS
        if unknown_fields:
            logger.warning(
                "Campos desconhecidos na resposta do LLM",
                extra={"unknown_fields": list(unknown_fields)},
            )

        # Verificar campos faltando
        missing_fields = EXPECTED_FIELDS - set(data.keys())
        if missing_fields:
            if self.allow_partial:
                logger.info(
                    "Campos faltando na resposta (preenchendo com null)",
                    extra={"missing_fields": list(missing_fields)},
                )
                # Preencher campos faltando com None
                for field in missing_fields:
                    data[field] = None
            else:
                raise JSONParsingError(
                    message="Campos obrigatórios faltando na resposta",
                    details=f"Campos faltando: {missing_fields}",
                )

        # Validar e normalizar cada campo
        validated = {}
        for field in EXPECTED_FIELDS:
            value = data.get(field)
            validated[field] = self._normalize_field(field, value)

        return validated

    def _normalize_field(self, field: str, value: Any) -> Optional[str]:
        """Normaliza valor de um campo"""
        # Tratar valores nulos
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ("null", "none", "n/a", "na", "", "-"):
                return None

        # Converter para string se necessário
        if not isinstance(value, str):
            logger.warning(
                f"Campo {field} não é string, convertendo",
                extra={"field": field, "type": type(value).__name__},
            )
            value = str(value)

        # Validações específicas por campo
        if field == "data_ocorrencia":
            return self._validate_date(value)

        return value if value else None

    def _validate_date(self, value: str) -> Optional[str]:
        """
        Valida formato de data.
        A normalização final é feita pelo Pydantic no IncidentResponse.
        """
        if not value or value.lower() in ("null", "none"):
            return None

        # Verificar se contém pelo menos números que parecem data
        if not re.search(r"\d{2,4}[-/]\d{1,2}[-/]\d{1,2}", value):
            logger.warning(
                "Formato de data não reconhecido",
                extra={"value": value},
            )
            # Retornar mesmo assim, o Pydantic tentará normalizar

        return value


class OllamaService:
    """Cliente para comunicacao com API Ollama"""

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: float = None,
    ):
        settings = get_settings()

        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        self.max_retries = settings.ollama_max_retries
        self.client = httpx.AsyncClient(timeout=self.timeout)

        # Configurar validador de resposta
        self.validator = ResponseValidator(
            allow_partial=settings.allow_partial_response
        )
        self.validate_response = settings.validate_llm_response

        logger.info(
            "OllamaService inicializado",
            extra={
                "base_url": self.base_url,
                "model": self.model,
                "timeout": self.timeout,
                "validate_response": self.validate_response,
            },
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

        # Extrair JSON da resposta
        json_data = self._extract_json_robust(response)

        # Validar schema se habilitado
        if self.validate_response:
            json_data = self.validator.validate(json_data)

        # Criar objeto de resposta (Pydantic faz validação adicional)
        incident_data = IncidentResponse(**json_data)

        logger.info(
            "Extracao concluida com sucesso",
            extra={
                "has_date": incident_data.data_ocorrencia is not None,
                "has_local": incident_data.local is not None,
                "has_tipo": incident_data.tipo_incidente is not None,
                "has_impacto": incident_data.impacto is not None,
            },
        )

        return incident_data

    async def _generate_with_retry(self, prompt: str, max_retries: int = None) -> str:
        """
        Envia prompt para o modelo Ollama com retry

        Raises:
            LLMConnectionError: Após todas tentativas falharem por conexão
            LLMTimeoutError: Após todas tentativas falharem por timeout
        """
        retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(retries):
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
                        "max_retries": retries,
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
                        "max_retries": retries,
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

    def _extract_json_robust(self, text: str) -> Dict:
        """
        Extrai JSON de forma robusta usando regex.

        Estratégia:
        1. Remove marcadores markdown
        2. Busca objeto JSON usando regex robusto
        3. Valida balanceamento de chaves
        4. Tenta parsear
        """
        logger.info(
            "Processando resposta do LLM",
            extra={"response_preview": text[:200] if text else "empty"},
        )

        if not text:
            raise JSONParsingError(
                message="Resposta vazia do LLM",
                details="Nenhum conteúdo retornado",
            )

        # Remove marcadores markdown
        cleaned = text.replace("```json", "").replace("```", "").strip()

        # Regex robusto: encontra objetos JSON completos
        # Captura desde { até } correspondente, permitindo nested objects
        json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"

        matches = re.finditer(json_pattern, cleaned, re.DOTALL)

        # Tenta parsear cada match, preferindo o maior
        candidates = []
        for match in matches:
            json_str = match.group(0)
            if self._is_balanced_json(json_str):
                candidates.append(json_str)

        if not candidates:
            raise JSONParsingError(
                message="Resposta do LLM não contém JSON válido",
                details=cleaned[:200],
            )

        # Tenta parsear candidatos (do maior para o menor)
        candidates.sort(key=len, reverse=True)

        for json_str in candidates:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

        # Se nenhum funcionou, tenta estratégia de fallback
        return self._extract_json_fallback(cleaned)

    def _is_balanced_json(self, text: str) -> bool:
        """Verifica se chaves estão balanceadas"""
        stack = []
        for char in text:
            if char == "{":
                stack.append(char)
            elif char == "}":
                if not stack:
                    return False
                stack.pop()
        return len(stack) == 0

    def _extract_json_fallback(self, text: str) -> Dict:
        """
        Estratégia de fallback: encontra primeira { e última } balanceada
        """
        start = text.find("{")
        if start == -1:
            raise JSONParsingError(
                message="Resposta do LLM não contém JSON",
                details=text[:200],
            )

        # Encontra } correspondente
        brace_count = 0
        end = None

        for i in range(start, len(text)):
            char = text[i]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i
                    break

        if end is not None:
            json_str = text[start : end + 1]
        else:
            # Tenta adicionar chaves faltando
            candidate = text[start:].rstrip(" \n\r\t.;,")
            open_braces = candidate.count("{")
            close_braces = candidate.count("}")
            if close_braces < open_braces:
                candidate = candidate + ("}" * (open_braces - close_braces))
            json_str = candidate

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(
                "Erro ao parsear JSON",
                extra={
                    "error": str(e),
                    "json_preview": json_str[:200],
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
