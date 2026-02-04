"""Testes unitarios para o preprocessador"""

import pytest
from datetime import datetime
from app.services.preprocessor import IncidentPreprocessor


class TestIncidentPreprocessor:
    """Testes para a classe IncidentPreprocessor"""

    def test_normalize_whitespace(self, preprocessor):
        """Deve normalizar espacos duplicados"""
        text = "Texto   com    muitos     espacos"
        result = preprocessor._normalize_whitespace(text)
        assert result == "Texto com muitos espacos"

    def test_normalize_whitespace_newlines(self, preprocessor):
        """Deve normalizar quebras de linha"""
        text = "Texto\ncom\n\nquebras\n\n\nde linha"
        result = preprocessor._normalize_whitespace(text)
        assert result == "Texto com quebras de linha"

    def test_normalize_whitespace_trim(self, preprocessor):
        """Deve remover espacos no inicio e fim"""
        text = "   texto com espacos   "
        result = preprocessor._normalize_whitespace(text)
        assert result == "texto com espacos"

    def test_normalize_relative_dates_hoje(self, preprocessor):
        """Deve normalizar 'HOJE' para 'hoje'"""
        text = "HOJE houve um incidente"
        result = preprocessor._normalize_relative_dates(text)
        assert "hoje" in result

    def test_normalize_relative_dates_ontem(self, preprocessor):
        """Deve normalizar 'ONTEM' para 'ontem'"""
        text = "ONTEM houve um incidente"
        result = preprocessor._normalize_relative_dates(text)
        assert "ontem" in result

    def test_normalize_relative_dates_anteontem(self, preprocessor):
        """Deve normalizar 'ANTEONTEM' para 'anteontem'"""
        text = "ANTEONTEM houve um incidente"
        result = preprocessor._normalize_relative_dates(text)
        assert "anteontem" in result

    def test_clean_special_chars_keeps_punctuation(self, preprocessor):
        """Deve manter pontuacao basica"""
        text = "Texto com pontuacao: virgula, ponto. Exclamacao! Interrogacao?"
        result = preprocessor._clean_special_chars(text)
        assert ":" in result
        assert "," in result
        assert "." in result
        assert "!" in result
        assert "?" in result

    def test_clean_special_chars_keeps_accents(self, preprocessor):
        """Deve manter acentuacao portuguesa"""
        text = "Sao Paulo, Brasilia, acao, informacao"
        result = preprocessor._clean_special_chars(text)
        assert "Sao" in result
        assert "Brasilia" in result
        assert "acao" in result

    def test_clean_special_chars_removes_invalid(self, preprocessor):
        """Deve remover caracteres invalidos"""
        text = "Texto com #hashtag e $dolar e %percentual"
        result = preprocessor._clean_special_chars(text)
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result

    def test_preprocess_returns_tuple(self, preprocessor):
        """Deve retornar tupla com texto e data"""
        text = "Incidente de teste"
        result = preprocessor.preprocess(text)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_preprocess_returns_reference_date(self, preprocessor):
        """Deve retornar data de referencia no formato correto"""
        text = "Incidente de teste"
        _, reference_date = preprocessor.preprocess(text)
        assert reference_date == "2025-02-04"

    def test_preprocess_full_pipeline(self, preprocessor):
        """Deve processar texto completo corretamente"""
        text = "   ONTEM   houve um incidente #grave   "
        processed_text, _ = preprocessor.preprocess(text)
        assert processed_text == "ontem houve um incidente grave"

    def test_set_reference_date(self):
        """Deve permitir alterar data de referencia"""
        prep = IncidentPreprocessor()
        new_date = datetime(2025, 1, 15, 10, 30, 0)
        prep.set_reference_date(new_date)
        _, reference_date = prep.preprocess("teste")
        assert reference_date == "2025-01-15"
