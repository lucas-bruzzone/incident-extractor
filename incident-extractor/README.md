# Incident Information Extractor API

API REST para extração automática de informações estruturadas de descrições de incidentes usando LLM local (Ollama).

## Arquitetura da Solução

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Cliente   │─────▶│  FastAPI     │─────▶│   Ollama    │
│   (HTTP)    │◀─────│  (API REST)  │◀─────│   (LLM)     │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │Preprocessor  │
                     │   Pipeline   │
                     └──────────────┘
```

### Componentes Principais

- **FastAPI**: Framework web assíncrono com validação Pydantic
- **Ollama**: Servidor LLM local (modelo tinyllama - 637MB)
- **Preprocessor**: Pipeline de normalização de texto
- **Prompt Engineering**: Templates estruturados com few-shot examples

## Requisitos

- Docker e Docker Compose
- **4GB RAM disponível** (2GB para Ollama + 1GB para API + 1GB sistema)
- Portas 8000 e 11434 disponíveis

**Docker Desktop:** Configure em Settings → Resources → Memory ≥ 4GB

## Setup Rápido

### Windows

```powershell
# 1. Inicie os containers
docker-compose up -d

# 2. Execute o setup (baixa o modelo - aguarde ~5min)
.\setup.ps1

# 3. Teste
curl http://localhost:8000/health
```

### Linux/Mac

```bash
# 1. Inicie os containers
docker-compose up -d

# 2. Execute o setup (baixa o modelo - aguarde ~5min)
chmod +x setup.sh
./setup.sh

# 3. Teste
curl http://localhost:8000/health
```

O setup inicial baixa o modelo tinyllama (~637MB). Execute apenas uma vez.

## Uso da API

### Endpoint Principal: POST /extract-incident

**Request:**
```bash
curl -X POST "http://localhost:8000/extract-incident" \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
  }'
```

**Response:**
```json
{
  "data_ocorrencia": "2025-02-03 14:00",
  "local": "São Paulo",
  "tipo_incidente": "Falha no servidor",
  "impacto": "Sistema de faturamento indisponível por 2 horas"
}
```

### Exemplo com Python

```python
import requests

url = "http://localhost:8000/extract-incident"
payload = {
    "descricao": "Hoje pela manhã houve queda de energia no data center de Brasília."
}

response = requests.post(url, json=payload)
print(response.json())
```

### Documentação Interativa

Acesse a documentação Swagger em: `http://localhost:8000/docs`

## Estrutura do Projeto

```
incident-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI principal
│   ├── models.py            # Schemas Pydantic (request/response)
│   ├── prompts.py           # Templates de prompt para LLM
│   └── services/
│       ├── __init__.py
│       ├── llm_service.py   # Cliente Ollama
│       └── preprocessor.py  # Pipeline de pré-processamento
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Pipeline de Processamento

1. **Recebimento**: API recebe descrição via POST
2. **Pré-processamento**:
   - Normalização de espaços e caracteres
   - Conversão de datas relativas
   - Limpeza de caracteres especiais
3. **Prompt Engineering**: Construção de prompt estruturado com examples
4. **Extração LLM**: Chamada ao Ollama com temperatura baixa (0.1)
5. **Validação**: Parse e validação do JSON com Pydantic
6. **Resposta**: Retorno estruturado ao cliente

## Configuração Avançada

### Variáveis de Ambiente

Edite `docker-compose.yml` para customizar:

```yaml
environment:
  - OLLAMA_BASE_URL=http://ollama:11434  # URL do Ollama
  - OLLAMA_MODEL=tinyllama               # Modelo a ser usado
```

### Modelos Alternativos

Para usar outro modelo (ex: mistral):

```bash
# Entre no container do Ollama
docker exec -it incident-ollama ollama pull mistral

# Atualize OLLAMA_MODEL no docker-compose.yml e reinicie
docker-compose restart api
```

### Execução Local (sem Docker)

```bash
# 1. Instale dependências
pip install -r requirements.txt

# 2. Inicie o Ollama separadamente
ollama serve &
ollama pull tinyllama

# 3. Execute a API
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Endpoints Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Informações da API |
| `/health` | GET | Status da API e Ollama |
| `/extract-incident` | POST | Extrai informações de incidente |
| `/models` | GET | Lista modelos disponíveis no Ollama |
| `/docs` | GET | Documentação Swagger |

## Decisões Técnicas

### Por que tinyllama?
- Modelo muito pequeno (~637MB) ideal para demonstração
- Roda localmente sem custos de API
- Execução rápida mesmo em máquinas modestas
- Suficiente para validar arquitetura e integração

### Por que FastAPI?
- Validação automática com Pydantic
- Documentação interativa (Swagger)
- Performance assíncrona
- Type hints nativos

### Pipeline de Pré-processamento
- Melhora consistência das entradas
- Facilita interpretação pelo LLM
- Normaliza datas relativas

### Prompt Engineering
- Few-shot examples aumentam precisão
- Instruções explícitas para formato JSON
- Temperatura baixa (0.1) para determinismo

## Troubleshooting

### Erro de memória ou Ollama não inicia
```powershell
# Verifique memória disponível no Docker Desktop
# Settings → Resources → Memory ≥ 4GB

# Reinicie os containers
docker-compose restart
```

### Setup não baixou o modelo
```powershell
# Execute manualmente
docker exec incident-ollama ollama pull tinyllama

# Verifique se foi baixado
docker exec incident-ollama ollama list
```

### API não conecta ao Ollama
```bash
# Verifique se o Ollama está rodando
docker ps | grep ollama

# Verifique logs
docker logs incident-ollama

# Reinicie o serviço
docker-compose restart ollama
```

### Modelo não está baixado
```bash
# Entre no container e baixe manualmente
docker exec -it incident-ollama ollama pull tinyllama
```

### API retorna erro 500
```bash
# Verifique logs da API
docker logs incident-api

# Teste a conexão manualmente
curl http://localhost:11434/api/tags
```

### Porta já em uso
```bash
# Mude a porta no docker-compose.yml
ports:
  - "8001:8000"  # Usa 8001 no host
```

## Melhorias Futuras

- [ ] Cache de respostas para textos similares
- [ ] Suporte a múltiplos idiomas
- [ ] Métricas de observabilidade (Prometheus)
- [ ] Testes automatizados (pytest)
- [ ] CI/CD com GitHub Actions
- [ ] Deploy em cloud (AWS Lambda + API Gateway)

## Contato

Desenvolvido por Lucas Bruzzone para o teste técnico A3Data

- GitHub: [lucas-bruzzone](https://github.com/lucas-bruzzone)
- LinkedIn: [lucas-bruzzone](https://linkedin.com/in/lucas-bruzzone)
