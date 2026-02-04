"""Servico de integracao com Ollama LLM"""

import httpx
import json
import logging
import os
import asyncio
from typing import Dict
from app.models import IncidentResponse
from app.prompts import build_extraction_prompt

logger = logging.getLogger(__name__)


class OllamaService:
    """Cliente para comunicacao com API Ollama"""
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: float = 180.0
    ):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "tinyllama")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
        logger.info(f"OllamaService inicializado: {self.base_url} | Modelo: {self.model}")
    
    async def extract_incident_info(
        self,
        incident_description: str,
        reference_date: str
    ) -> IncidentResponse:
        """
        Extrai informacoes estruturadas de um incidente usando LLM
        """
        try:
            prompt = build_extraction_prompt(incident_description, reference_date)
            
            logger.info(f"Enviando requisicao para Ollama (modelo: {self.model})")
            
            response = await self._generate_with_retry(prompt)
            
            json_data = self._extract_json(response)
            
            incident_data = IncidentResponse(**json_data)
            
            logger.info("Extracao concluida com sucesso")
            return incident_data
            
        except Exception as e:
            logger.error(f"Erro na extracao de informacoes: {str(e)}")
            raise
    
    async def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """
        Envia prompt para o modelo Ollama com retry
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await self._generate(prompt)
            except Exception as e:
                last_error = e
                wait_time = 2 ** attempt
                logger.warning(f"Tentativa {attempt + 1}/{max_retries} falhou: {str(e)}. Aguardando {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        raise last_error
    
    async def _generate(self, prompt: str) -> str:
        """
        Envia prompt para o modelo Ollama
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP ao chamar Ollama: {e.response.status_code}")
            raise Exception(f"Erro ao comunicar com Ollama: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Erro de conexao com Ollama: {str(e)}")
            raise Exception(f"Nao foi possivel conectar ao Ollama: {str(e)}")
    
    def _extract_json(self, text: str) -> Dict:
        """
        Extrai JSON da resposta do LLM
        """
        logger.info(f"Resposta do LLM (primeiros 500 chars): {text[:500]}")
        
        text = text.strip()
        text = text.replace("```json", "").replace("```", "")
        text = text.strip()
        
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            logger.error(f"Nao ha chaves na resposta: {text[:200]}")
            raise Exception("Resposta do LLM nao contem JSON valido")
        
        json_str = text[start_idx:end_idx + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {str(e)}")
            logger.error(f"JSON problematico: {json_str}")
            
            import re
            json_str_fixed = re.sub(r'"\s*\n\s*', '" ', json_str)
            
            try:
                return json.loads(json_str_fixed)
            except json.JSONDecodeError:
                raise Exception(f"Resposta do LLM nao contem JSON valido: {str(e)}")
    
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
