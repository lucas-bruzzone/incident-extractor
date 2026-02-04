"""Pipeline de pre-processamento de texto de incidentes"""

import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IncidentPreprocessor:
    """Pre-processador para normalizacao de descricoes de incidentes"""

    def __init__(self):
        self.reference_date = datetime.now()

    def preprocess(self, text: str) -> tuple:
        """
        Pre-processa o texto do incidente

        Returns:
            Tupla com (texto processado, data de referencia)
        """
        processed_text = self._normalize_whitespace(text)
        processed_text = self._normalize_relative_dates(processed_text)
        processed_text = self._clean_special_chars(processed_text)
        reference_date = self.reference_date.strftime("%Y-%m-%d")

        logger.info(f"Texto pre-processado. Data de referencia: {reference_date}")

        return processed_text, reference_date

    def _normalize_whitespace(self, text: str) -> str:
        """Remove espacos duplicados e normaliza quebras de linha"""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _normalize_relative_dates(self, text: str) -> str:
        """Normaliza expressoes de datas relativas"""
        text = re.sub(r"\bhoje\b", "hoje", text, flags=re.IGNORECASE)
        text = re.sub(r"\bontem\b", "ontem", text, flags=re.IGNORECASE)
        text = re.sub(r"\banteontem\b", "anteontem", text, flags=re.IGNORECASE)
        return text

    def _clean_special_chars(self, text: str) -> str:
        """Remove caracteres especiais problematicos"""
        text = re.sub(r"[^\w\s\.,;:!?@\-\/áàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]", "", text)
        return text

    def set_reference_date(self, date: datetime):
        """Define uma data de referencia customizada"""
        self.reference_date = date
        logger.info(f"Data de referencia atualizada para: {date}")
