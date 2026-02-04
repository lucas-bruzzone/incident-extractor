"""Pipeline de pré-processamento de texto de incidentes"""

import re
from datetime import datetime, timedelta
from dateutil import parser
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class IncidentPreprocessor:
    """Pré-processador para normalização de descrições de incidentes"""
    
    RELATIVE_DATE_PATTERNS = {
        r'\bhoje\b': 0,
        r'\bontem\b': -1,
        r'\banteontem\b': -2,
        r'\bhá\s+(\d+)\s+dias?\b': None,  # Requer parsing do número
    }
    
    def __init__(self):
        self.reference_date = datetime.now()
    
    def preprocess(self, text: str) -> Tuple[str, str]:
        """
        Pré-processa o texto do incidente
        
        Args:
            text: Texto original da descrição
            
        Returns:
            Tupla com (texto processado, data de referência)
        """
        # Normaliza espaços e quebras de linha
        processed_text = self._normalize_whitespace(text)
        
        # Normaliza datas relativas no texto
        processed_text = self._normalize_relative_dates(processed_text)
        
        # Remove caracteres especiais problemáticos
        processed_text = self._clean_special_chars(processed_text)
        
        # Formata data de referência
        reference_date = self.reference_date.strftime("%Y-%m-%d")
        
        logger.info(f"Texto pré-processado. Data de referência: {reference_date}")
        
        return processed_text, reference_date
    
    def _normalize_whitespace(self, text: str) -> str:
        """Remove espaços duplicados e normaliza quebras de linha"""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _normalize_relative_dates(self, text: str) -> str:
        """
        Converte expressões de datas relativas em formato mais explícito
        Mantém as expressões originais para o LLM interpretar com a data de referência
        """
        # O LLM receberá a data de referência e interpretará "ontem", "hoje", etc.
        # Aqui apenas garantimos que o formato está limpo
        text = re.sub(r'\bhoje\b', 'hoje', text, flags=re.IGNORECASE)
        text = re.sub(r'\bontem\b', 'ontem', text, flags=re.IGNORECASE)
        text = re.sub(r'\banteontem\b', 'anteontem', text, flags=re.IGNORECASE)
        
        return text
    
    def _clean_special_chars(self, text: str) -> str:
        """Remove caracteres especiais que podem causar problemas no parsing"""
        # Mantém pontuação básica e acentuação
        text = re.sub(r'[^\w\s\.,;:!?@\-\/áàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]', '', text)
        return text
    
    def set_reference_date(self, date: datetime):
        """
        Define uma data de referência customizada (útil para testes)
        
        Args:
            date: Data de referência
        """
        self.reference_date = date
        logger.info(f"Data de referência atualizada para: {date}")
