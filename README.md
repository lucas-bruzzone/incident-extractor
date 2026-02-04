# Incident Information Extractor API

API REST para extracao automatica de informacoes estruturadas de descricoes de incidentes usando LLM local (Ollama).

## Arquitetura

```
Cliente (HTTP) --> FastAPI (API REST) --> Ollama (qwen2:0.5b)
                        |
                        v
                   Preprocessor
```

## Requisitos

- Docker e Docker Compose
- 2GB RAM disponivel
- Portas 8000 e 11434 disponiveis

## Setup Rapido

```bash
# 1. Inicie os containers (o modelo sera baixado automaticamente)
docker-compose up -d --build

# 2. Aguarde o download do modelo (~400MB, primeira execucao)
docker logs -f incident-api

# 3. Teste quando a API estiver pronta
curl http://localhost:8000/health
```

## Uso da API

### POST /extract-incident

```bash
curl -X POST "http://localhost:8000/extract-incident" \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Ontem as 14h, no escritorio de Sao Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
  }'
```

**Resposta:**
```json
{
  "data_ocorrencia": "2025-02-03 14:00",
  "local": "Sao Paulo",
  "tipo_incidente": "Falha no servidor",
  "impacto": "Sistema de faturamento indisponivel por 2 horas"
}
```

### Documentacao Interativa

Acesse: http://localhost:8000/docs

## Endpoints

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/` | GET | Informacoes da API |
| `/health` | GET | Status da API e Ollama |
| `/extract-incident` | POST | Extrai informacoes de incidente |
| `/models` | GET | Lista modelos disponiveis |
| `/docs` | GET | Documentacao Swagger |

## Estrutura do Projeto

```
incident-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI
│   ├── models.py            # Schemas Pydantic
│   ├── prompts.py           # Templates de prompt
│   └── services/
│       ├── __init__.py
│       ├── llm_service.py   # Cliente Ollama
│       └── preprocessor.py  # Pre-processamento
├── tests/
│   ├── conftest.py          # Fixtures
│   ├── test_api.py          # Testes da API
│   ├── test_llm_service.py  # Testes do LLM service
│   ├── test_models.py       # Testes dos models
│   ├── test_preprocessor.py # Testes do preprocessor
│   └── test_prompts.py      # Testes dos prompts
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
└── README.md
```

## Testes

O projeto inclui testes unitarios e de integracao com pytest.

### Executar testes localmente

```bash
# Instale as dependencias
pip install -r requirements.txt

# Execute todos os testes
pytest tests/ -v

# Execute com cobertura
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Executar testes no Docker

```bash
docker-compose exec api pytest tests/ -v
```

### Estrutura dos testes

```
tests/
├── conftest.py          # Fixtures compartilhadas
├── test_api.py          # Testes de integracao da API
├── test_llm_service.py  # Testes do cliente Ollama
├── test_models.py       # Testes dos schemas Pydantic
├── test_preprocessor.py # Testes do pre-processador
└── test_prompts.py      # Testes do modulo de prompts
```

## Troubleshooting

### API nao conecta ao Ollama
```bash
# Verifique os logs
docker logs incident-api
docker logs incident-ollama

# Reinicie
docker-compose down && docker-compose up -d --build
```

### Modelo nao baixado
```bash
# Baixe manualmente
docker exec incident-ollama ollama pull qwen2:0.5b
```

### Timeout na requisicao
A primeira requisicao pode demorar mais (carregamento do modelo na memoria). Aguarde ate 3 minutos.

## Decisoes Tecnicas

- **qwen2:0.5b**: Modelo ultra-leve (~400MB), ideal para ambientes com recursos limitados. Roda localmente sem custos de API
- **FastAPI**: Validacao automatica com Pydantic, documentacao Swagger interativa, suporte async nativo
- **Retry com backoff**: Resiliencia em caso de falhas temporarias de conexao
- **Healthcheck Docker**: Garante que Ollama esta pronto antes da API iniciar
- **Entrypoint automatizado**: Baixa o modelo automaticamente na primeira execucao

## Proximos Passos

### Curto Prazo
- [x] Adicionar testes unitarios e de integracao (pytest)
- [ ] Implementar cache de respostas para textos similares (Redis)
- [ ] Adicionar validacao de formato de data no response
- [ ] Melhorar tratamento de erros com mensagens mais descritivas

### Medio Prazo
- [ ] Suporte a multiplos idiomas no prompt
- [ ] Endpoint de batch processing para multiplos incidentes
- [ ] Metricas de observabilidade (Prometheus/Grafana)
- [ ] Rate limiting para protecao da API
- [ ] Autenticacao via API Key ou JWT

### Longo Prazo
- [ ] CI/CD com GitHub Actions
- [ ] Deploy em cloud (AWS ECS/Lambda ou GCP Cloud Run)
- [ ] Fine-tuning do modelo para dominio especifico de incidentes
- [ ] Interface web para submissao de incidentes
- [ ] Integracao com sistemas de ticketing (Jira, ServiceNow)

---

Desenvolvido para o teste tecnico A3Data
