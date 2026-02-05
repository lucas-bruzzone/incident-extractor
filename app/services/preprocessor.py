"""Pipeline de pre-processamento de texto de incidentes"""

import re
from datetime import datetime, timedelta
from typing import Tuple
from app.logging_config import get_logger

logger = get_logger(__name__)


class IncidentPreprocessor:
    """Pre-processador para normalizacao de descricoes de incidentes"""

    # Mapeamento de meses em português
    MESES_PT = {
        "janeiro": 1,
        "fevereiro": 2,
        "marco": 3,
        "março": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
        "jan": 1,
        "fev": 2,
        "mar": 3,
        "abr": 4,
        "mai": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "set": 9,
        "out": 10,
        "nov": 11,
        "dez": 12,
    }

    def __init__(self):
        self.reference_date = datetime.now()

    def preprocess(self, text: str) -> Tuple[str, str]:
        """
        Pre-processa o texto do incidente

        Returns:
            Tupla com (texto processado, data de referencia)
        """
        processed_text = self._normalize_whitespace(text)
        processed_text = self._resolve_dates(processed_text)
        processed_text = self._clean_special_chars(processed_text)
        reference_date = self.reference_date.strftime("%Y-%m-%d")

        logger.info(
            "Texto pre-processado",
            extra={
                "original_length": len(text),
                "processed_length": len(processed_text),
                "reference_date": reference_date,
            },
        )

        return processed_text, reference_date

    def _normalize_whitespace(self, text: str) -> str:
        """Remove espacos duplicados e normaliza quebras de linha"""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _resolve_dates(self, text: str) -> str:
        """
        Resolve todas as expressões de data para formato absoluto ISO.

        Transforma:
        - "hoje" -> "no dia 2026-02-04"
        - "ontem" -> "no dia 2026-02-03"
        - "dia 27/01" -> "no dia 2026-01-27"
        - "15 de janeiro" -> "no dia 2026-01-15"
        """
        text = self._resolve_relative_dates_simple(text)
        text = self._resolve_date_ddmmyyyy(text)
        text = self._resolve_date_ddmm(text)
        text = self._resolve_date_extenso(text)
        text = self._normalize_time(text)
        return text

    def _resolve_relative_dates_simple(self, text: str) -> str:
        """Resolve datas relativas (hoje, ontem, anteontem)"""
        # Mapa de palavras -> dias atrás
        relative_words = {"hoje": 0, "ontem": 1, "anteontem": 2}

        for word, days_ago in relative_words.items():
            text = self._resolve_single_relative_date(text, word, days_ago)

        return text

    def _resolve_single_relative_date(self, text: str, word: str, days_ago: int) -> str:
        """Resolve uma única palavra relativa (hoje, ontem, anteontem)"""
        date_str = self._get_relative_date(days_ago)

        # Padrões em ordem de especificidade (do mais específico ao mais genérico)
        patterns = [
            # Com horário explícito: "hoje às 10h30"
            (
                rf"\b{word}\s+(?:às|as)\s*(\d{{1,2}})(?::(\d{{2}}))?(?:\s*h(?:oras?)?)?\b",
                lambda m: f"no dia {date_str} às {m.group(1).zfill(2)}:{m.group(2) or '00'}",
            ),
            # Período: "hoje pela manhã"
            (
                rf"\b{word}\s+(?:pela manhã|pela manha|de manhã|de manha)\b",
                lambda m: f"no dia {date_str} às 09:00",
            ),
            (
                rf"\b{word}\s+(?:à tarde|a tarde|de tarde)\b",
                lambda m: f"no dia {date_str} às 14:00",
            ),
            (
                rf"\b{word}\s+(?:à noite|a noite|de noite)\b",
                lambda m: f"no dia {date_str} às 20:00",
            ),
            # Palavra sozinha: "hoje"
            (rf"\b{word}\b", lambda m: f"no dia {date_str}"),
        ]

        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _get_relative_date(self, days_ago: int) -> str:
        """Retorna data no formato ISO para N dias atrás"""
        target_date = self.reference_date - timedelta(days=days_ago)
        return target_date.strftime("%Y-%m-%d")

    def _resolve_date_ddmmyyyy(self, text: str) -> str:
        """Resolve datas no formato DD/MM/YYYY ou DD/MM/YY"""

        def replace_date(match: re.Match) -> str:
            prefix = match.group(1) or ""
            day = int(match.group(2))
            month = int(match.group(3))
            year = match.group(4)

            # Converter ano de 2 dígitos para 4
            if len(year) == 2:
                year_int = int(year)
                year = 2000 + year_int if year_int < 50 else 1900 + year_int
            else:
                year = int(year)

            # Validar data
            try:
                datetime(year, month, day)
                return f"{prefix}no dia {year}-{month:02d}-{day:02d}"
            except ValueError:
                return match.group(0)  # Data inválida, manter original

        # Padrão: "dia 27/01/2026", "em 27/01/26", "27/01/2026"
        pattern = r"((?:dia|em|de)\s+)?(\d{1,2})/(\d{1,2})/(\d{2,4})"
        return re.sub(pattern, replace_date, text, flags=re.IGNORECASE)

    def _resolve_date_ddmm(self, text: str) -> str:
        """Resolve datas no formato DD/MM (assume ano atual ou anterior)"""

        def replace_date(match: re.Match) -> str:
            prefix = match.group(1) or ""
            day = int(match.group(2))
            month = int(match.group(3))

            # Usar ano da data de referência
            year = self.reference_date.year

            # Se a data for futura, assumir ano anterior
            try:
                candidate_date = datetime(year, month, day)
                if candidate_date > self.reference_date:
                    year -= 1
                    candidate_date = datetime(year, month, day)

                return f"{prefix}no dia {year}-{month:02d}-{day:02d}"
            except ValueError:
                return match.group(0)  # Data inválida, manter original

        # Padrão: "dia 27/01", "em 27/01" - mas NÃO seguido de mais dígitos
        pattern = r"((?:dia|em|de)\s+)?(\d{1,2})/(\d{1,2})(?!/\d)"
        return re.sub(pattern, replace_date, text, flags=re.IGNORECASE)

    def _resolve_date_extenso(self, text: str) -> str:
        """Resolve datas por extenso (15 de janeiro, 20 de março de 2025)"""

        def replace_date(match: re.Match) -> str:
            prefix = match.group(1) or ""
            day = int(match.group(2))
            month_name = match.group(3).lower()
            year = match.group(4)

            month = self.MESES_PT.get(month_name)
            if not month:
                return match.group(0)

            if year:
                year = int(year)
            else:
                year = self.reference_date.year
                # Se a data for futura, assumir ano anterior
                try:
                    if datetime(year, month, day) > self.reference_date:
                        year -= 1
                except ValueError:
                    return match.group(0)

            try:
                datetime(year, month, day)  # Validar
                return f"{prefix}no dia {year}-{month:02d}-{day:02d}"
            except ValueError:
                return match.group(0)

        # Meses por extenso
        meses_pattern = "|".join(self.MESES_PT.keys())

        # Padrão: "15 de janeiro", "dia 20 de março de 2025"
        pattern = rf"((?:dia|em|de)\s+)?(\d{{1,2}})\s+de\s+({meses_pattern})(?:\s+de\s+(\d{{4}}))?"
        return re.sub(pattern, replace_date, text, flags=re.IGNORECASE)

    def _normalize_time(self, text: str) -> str:
        """Normaliza formatos de horário para HH:MM"""

        def complex_replace(match: re.Match) -> str:
            prefix = match.group(1)
            hour = match.group(2).zfill(2)
            minute = match.group(3) or match.group(4) or "00"
            return f"{prefix}{hour}:{minute}"

        # Padrões: "às 10h", "as 14h30", "às 9:30", "às 10 horas"
        pattern = r"(às\s+|as\s+)(\d{1,2})(?::(\d{2})|\s*h(?:oras?)?(\d{2})?)"
        return re.sub(pattern, complex_replace, text, flags=re.IGNORECASE)

    def _clean_special_chars(self, text: str) -> str:
        """Remove caracteres especiais problematicos"""
        text = re.sub(r"[^\w\s\.,;:!?@\-\/áàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]", "", text)
        return text

    def set_reference_date(self, date: datetime):
        """Define uma data de referencia customizada"""
        self.reference_date = date
        logger.info(
            "Data de referencia atualizada", extra={"new_date": date.isoformat()}
        )
