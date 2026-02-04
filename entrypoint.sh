#!/bin/bash
set -e

OLLAMA_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"
MODEL="${OLLAMA_MODEL:-qwen2:0.5b}"

echo "Aguardando Ollama em $OLLAMA_URL..."
until curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; do
    echo "Ollama ainda nao disponivel, aguardando..."
    sleep 5
done
echo "Ollama disponivel!"

echo "Verificando modelo $MODEL..."
if ! curl -s "$OLLAMA_URL/api/tags" | grep -q "$MODEL"; then
    echo "Baixando modelo $MODEL..."
    curl -X POST "$OLLAMA_URL/api/pull" -d "{\"name\": \"$MODEL\"}" --no-buffer
    echo "Modelo baixado!"
else
    echo "Modelo $MODEL ja esta disponivel."
fi

echo "Iniciando API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
