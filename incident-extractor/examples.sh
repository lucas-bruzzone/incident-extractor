#!/bin/bash

# Exemplos de uso da API Incident Extractor

BASE_URL="http://localhost:8000"

echo "================================================"
echo "Incident Information Extractor - Exemplos de Uso"
echo "================================================"
echo ""

# 1. Health Check
echo "1. Health Check"
echo "----------------------------------------"
curl -s "$BASE_URL/health" | jq .
echo ""
echo ""

# 2. Exemplo 1: Incidente com todas as informações
echo "2. Exemplo 1: Incidente completo"
echo "----------------------------------------"
curl -s -X POST "$BASE_URL/extract-incident" \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
  }' | jq .
echo ""
echo ""

# 3. Exemplo 2: Incidente hoje
echo "3. Exemplo 2: Incidente hoje"
echo "----------------------------------------"
curl -s -X POST "$BASE_URL/extract-incident" \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Hoje pela manhã, houve uma queda de energia no data center de Brasília afetando todos os serviços críticos."
  }' | jq .
echo ""
echo ""

# 4. Exemplo 3: Incidente sem data
echo "4. Exemplo 3: Incidente sem data específica"
echo "----------------------------------------"
curl -s -X POST "$BASE_URL/extract-incident" \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Vazamento de dados no banco de clientes detectado pela equipe de segurança. O impacto afetou aproximadamente 10.000 registros."
  }' | jq .
echo ""
echo ""

# 5. Exemplo 4: Incidente de rede
echo "5. Exemplo 4: Incidente de rede"
echo "----------------------------------------"
curl -s -X POST "$BASE_URL/extract-incident" \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Às 08:30 de hoje, detectamos intermitência na conexão com o provedor de internet no escritório de Belo Horizonte, causando lentidão generalizada nos sistemas web."
  }' | jq .
echo ""
echo ""

# 6. Exemplo 5: Incidente de segurança
echo "6. Exemplo 5: Incidente de segurança"
echo "----------------------------------------"
curl -s -X POST "$BASE_URL/extract-incident" \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Ontem à noite, por volta das 23h, foi identificada uma tentativa de acesso não autorizado aos servidores de produção da filial do Rio de Janeiro."
  }' | jq .
echo ""
echo ""

# 7. Listar modelos disponíveis
echo "7. Modelos disponíveis no Ollama"
echo "----------------------------------------"
curl -s "$BASE_URL/models" | jq .
echo ""

echo "================================================"
echo "Exemplos concluídos!"
echo "================================================"
