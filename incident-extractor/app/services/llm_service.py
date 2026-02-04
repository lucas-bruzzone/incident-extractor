"""Serviço de integração com Ollama LLM"""

import httpx
import json
import logging
import os
from typing import Dict, Optional
from app.models import IncidentResponse
from app.prompts import build_extraction_prompt

logger = logging.getLogger(__name__)


class OllamaService:
    """Cliente para comunicação com API Ollama"""
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: float = 60.0
    ):
        """
        Inicializa o serviço Ollama
        
        Args:
            base_url: URL base do serviço Ollama
            model: Nome do modelo a ser utilizado
            timeout: Timeout em segundos para requisições
        """
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
        Extrai informações estruturadas de um incidente usando LLM
        
        Args:
            incident_description: Descrição do incidente
            reference_date: Data de referência no formato YYYY-MM-DD
            
        Returns:
            IncidentResponse com informações extraídas
            
        Raises:
            Exception: Se houver erro na comunicação ou parsing
        """
        try:
            # Constrói o prompt
            prompt = build_extraction_prompt(incident_description, reference_date)
            
            logger.info(f"Enviando requisição para Ollama (modelo: {self.model})")
            
            # Faz a requisição ao Ollama
            response = await self._generate(prompt)
            
            # Extrai o JSON da resposta
            json_data = self._extract_json(response)
            
            # Valida e converte para o schema Pydantic
            incident_data = IncidentResponse(**json_data)
            
            logger.info("Extração concluída com sucesso")
            return incident_data
            
        except Exception as e:
            logger.error(f"Erro na extração de informações: {str(e)}")
            raise
    
    async def _generate(self, prompt: str) -> str:
        """
        Envia prompt para o modelo Ollama
        
        Args:
            prompt: Prompt formatado
            
        Returns:
            Resposta do modelo
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Baixa temperatura para respostas mais determinísticas
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
            logger.error(f"Erro de conexão com Ollama: {str(e)}")
            raise Exception(f"Não foi possível conectar ao Ollama: {str(e)}")
    
    def _extract_json(self, text: str) -> Dict:
        """
        Extrai JSON da resposta do LLM
        
        Args:
            text: Texto da resposta que pode conter JSON
            
        Returns:
            Dicionário com dados extraídos
        """
        # Log da resposta completa para debug
        logger.info(f"Resposta do LLM (primeiros 500 chars): {text[:500]}")
        
        # Remove possíveis marcadores de código markdown
        text = text.strip()
        text = text.replace("```json", "").replace("```", "")
        text = text.strip()
        
        # Tenta encontrar JSON entre chaves
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            logger.error(f"Não há chaves na resposta: {text[:200]}")
            raise Exception("Resposta do LLM não contém JSON válido")
        
        # Extrai apenas o conteúdo entre chaves
        json_str = text[start_idx:end_idx + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {str(e)}")
            logger.error(f"JSON problemático: {json_str}")
            
            # Tenta corrigir problemas comuns
            # Remove quebras de linha dentro de strings
            import re
            json_str_fixed = re.sub(r'"\s*\n\s*', '" ', json_str)
            
            try:
                return json.loads(json_str_fixed)
            except json.JSONDecodeError:
                raise Exception(f"Resposta do LLM não contém JSON válido: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Verifica se o serviço Ollama está disponível
        
        Returns:
            True se o serviço está disponível, False caso contrário
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
        """Fecha a conexão HTTP"""
        await self.client.aclose()
