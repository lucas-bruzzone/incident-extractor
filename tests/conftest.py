"""Fixtures compartilhadas para testes"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.services.preprocessor import IncidentPreprocessor
from app.models import IncidentResponse


def pytest_addoption(parser):
    """Adiciona opção de linha de comando para testes de integração"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Executa testes de integração com Ollama real",
    )


def pytest_configure(config):
    """Registra markers customizados"""
    config.addinivalue_line(
        "markers", "integration: marca testes que requerem Ollama real"
    )


def pytest_collection_modifyitems(config, items):
    """Pula testes de integração se --run-integration não for passado"""
    if config.getoption("--run-integration"):
        return

    skip_integration = pytest.mark.skip(reason="Requer --run-integration para executar")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture
def client():
    """Cliente de teste para a API"""
    return TestClient(app)


@pytest.fixture
def preprocessor():
    """Instancia do preprocessador com data fixa"""
    prep = IncidentPreprocessor()
    prep.set_reference_date(datetime(2025, 2, 4, 12, 0, 0))
    return prep


@pytest.fixture
def sample_incidents():
    """Exemplos de descricoes de incidentes para testes"""
    return [
        {
            "input": "Ontem as 14h, no escritorio de Sao Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas.",
            "expected": {
                "data_ocorrencia": "2025-02-03 14:00",
                "local": "Sao Paulo",
                "tipo_incidente": "Falha no servidor",
                "impacto": "Sistema de faturamento indisponivel por 2 horas",
            },
        },
        {
            "input": "Hoje pela manha houve queda de energia no data center de Brasilia.",
            "expected": {
                "data_ocorrencia": "2025-02-04 09:00",
                "local": "Brasilia",
                "tipo_incidente": "Queda de energia",
                "impacto": "Data center afetado",
            },
        },
        {
            "input": "Vazamento de dados detectado pela equipe de seguranca.",
            "expected": {
                "data_ocorrencia": None,
                "local": None,
                "tipo_incidente": "Vazamento de dados",
                "impacto": "Dados comprometidos",
            },
        },
    ]


@pytest.fixture
def mock_ollama_response():
    """Resposta mockada do Ollama"""
    return IncidentResponse(
        data_ocorrencia="2025-02-03 14:00",
        local="Sao Paulo",
        tipo_incidente="Falha no servidor",
        impacto="Sistema de faturamento indisponivel por 2 horas",
    )
