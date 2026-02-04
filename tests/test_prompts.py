"""Testes unitarios para o modulo de prompts"""

import pytest
from app.prompts import build_extraction_prompt, INCIDENT_EXTRACTION_PROMPT


class TestBuildExtractionPrompt:
    """Testes para a funcao build_extraction_prompt"""

    def test_prompt_contains_description(self):
        """Deve incluir descricao do incidente no prompt"""
        description = "Falha no servidor de producao"
        prompt = build_extraction_prompt(description, "2025-02-04")
        assert description in prompt

    def test_prompt_contains_reference_date(self):
        """Deve incluir data de referencia no prompt"""
        reference_date = "2025-02-04"
        prompt = build_extraction_prompt("Incidente teste", reference_date)
        assert reference_date in prompt

    def test_prompt_contains_json_instructions(self):
        """Deve conter instrucoes para retornar JSON"""
        prompt = build_extraction_prompt("Incidente", "2025-02-04")
        assert "JSON" in prompt

    def test_prompt_contains_expected_fields(self):
        """Deve mencionar os campos esperados"""
        prompt = build_extraction_prompt("Incidente", "2025-02-04")
        assert "data_ocorrencia" in prompt
        assert "local" in prompt
        assert "tipo_incidente" in prompt
        assert "impacto" in prompt

    def test_prompt_contains_examples(self):
        """Deve conter exemplos few-shot"""
        prompt = build_extraction_prompt("Incidente", "2025-02-04")
        assert "Sao Paulo" in prompt
        assert "Brasilia" in prompt

    def test_prompt_template_not_empty(self):
        """Template base nao deve estar vazio"""
        assert len(INCIDENT_EXTRACTION_PROMPT) > 0

    def test_prompt_format_placeholders(self):
        """Template deve ter placeholders corretos"""
        assert "{incident_description}" in INCIDENT_EXTRACTION_PROMPT
        assert "{reference_date}" in INCIDENT_EXTRACTION_PROMPT
