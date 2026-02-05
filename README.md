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

A descricao deve ter no minimo 10 caracteres.

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
| `/config` | GET | Configuracoes atuais da aplicacao |
| `/docs` | GET | Documentacao Swagger |

## Funcionalidades

### Logging Estruturado (JSON)

Todos os logs sao emitidos em formato JSON estruturado, facilitando integracao com ferramentas como ELK, Datadog, Splunk, etc.

Exemplo de log:
```json
{
  "timestamp": "2025-02-04T12:00:00.000Z",
  "level": "INFO",
  "logger": "app.main",
  "message": "Request processada",
  "service": "incident-extractor",
  "location": {"file": "main.py", "line": 95, "function": "add_request_context"},
  "extra": {
    "request_id": "abc-123",
    "method": "POST",
    "path": "/extract-incident",
    "status_code": 200,
    "duration_ms": 1234.56
  }
}
```

### Rate Limiting

Protecao contra abuso com limite de requisicoes por IP:

- `/extract-incident`: 10 requisicoes/minuto (configuravel via `RATE_LIMIT_EXTRACT`)
- Endpoints gerais: 60 requisicoes/minuto (configuravel via `RATE_LIMIT_DEFAULT`)

Headers de resposta incluem:
- `X-RateLimit-Limit`: Limite configurado
- `Retry-After`: Tempo de espera apos limite excedido

### Request Tracing

Cada requisicao recebe um `X-Request-ID` unico para rastreamento end-to-end.

## Estrutura do Projeto

```
incident-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI
│   ├── models.py            # Schemas Pydantic
│   ├── prompts.py           # Templates de prompt
│   ├── exceptions.py        # Excecoes customizadas
│   ├── config.py            # Configuracao centralizada
│   ├── logging_config.py    # Configuracao de logging JSON
│   ├── rate_limiter.py      # Configuracao de rate limiting
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
│   ├── test_prompts.py      # Testes dos prompts
│   ├── test_exceptions.py   # Testes das excecoes
│   ├── test_config.py       # Testes da configuracao
│   ├── test_logging_config.py # Testes do logging
│   ├── test_rate_limiter.py # Testes do rate limiter
│   └── test_integration.py  # Testes de integracao reais
├── .github/
│   └── workflows/
│       └── ci.yml           # Pipeline CI/CD
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
└── README.md
```

## Testes

### Testes Unitarios

```bash
# Instale as dependencias
pip install -r requirements.txt

# Execute todos os testes unitarios
pytest tests/ -v --ignore=tests/test_integration.py

# Execute com cobertura
pytest tests/ -v --cov=app --cov-report=term-missing --ignore=tests/test_integration.py
```

### Testes de Integracao

Testes que rodam contra Ollama real:

```bash
# Requer Ollama rodando localmente ou via Docker
pytest tests/test_integration.py -v --run-integration
```

### Executar testes no Docker

```bash
docker-compose exec api pytest tests/ -v --ignore=tests/test_integration.py
```

### CI/CD

O projeto inclui pipeline de CI/CD via GitHub Actions (`.github/workflows/ci.yml`) que executa:

1. **Job `test`**: Testes unitarios com cobertura de codigo
2. **Job `integration-test`**: Testes de integracao com Ollama real em container

O pipeline e executado automaticamente em pushes e pull requests para branches `main` e `master`.

## Variaveis de Ambiente

### Configuracao do Ollama

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL do servico Ollama |
| `OLLAMA_MODEL` | `qwen2:0.5b` | Modelo a ser utilizado |
| `OLLAMA_TIMEOUT` | `180.0` | Timeout em segundos (1-600) |
| `OLLAMA_MAX_RETRIES` | `3` | Tentativas em caso de falha (1-10) |

### Rate Limiting

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `RATE_LIMIT_EXTRACT` | `10/minute` | Limite para `/extract-incident` |
| `RATE_LIMIT_DEFAULT` | `60/minute` | Limite para outros endpoints |

### Logging e API

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `LOG_LEVEL` | `INFO` | Nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `SERVICE_NAME` | `incident-extractor` | Nome do servico nos logs |

### Validacao de Resposta do LLM

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `VALIDATE_LLM_RESPONSE` | `True` | Habilita validacao de schema |
| `ALLOW_PARTIAL_RESPONSE` | `True` | Permite respostas com campos null |

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

### Rate limit excedido
Aguarde o tempo indicado no header `Retry-After` ou ajuste os limites via variaveis de ambiente.

### Erro de validacao (422)
A descricao do incidente deve ter no minimo 10 caracteres.

## Decisoes Tecnicas

- **qwen2:0.5b**: Modelo ultra-leve (~400MB), ideal para ambientes com recursos limitados
- **FastAPI**: Validacao automatica com Pydantic, documentacao Swagger, suporte async
- **Logging JSON**: Facilita parsing e analise em ferramentas de observabilidade
- **Rate Limiting (slowapi)**: Protecao contra abuso, configuravel por endpoint
- **Retry com backoff**: Resiliencia em caso de falhas temporarias
- **Request ID**: Rastreabilidade de requisicoes end-to-end
- **pydantic-settings**: Configuracao centralizada com validacao

---

Desenvolvido para o teste tecnico A3Data
