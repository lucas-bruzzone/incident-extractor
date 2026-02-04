#!/bin/bash

echo "================================================"
echo "Setup Inicial - Incident Extractor"
echo "================================================"
echo ""

echo "Verificando se Ollama está rodando..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "Aguardando Ollama iniciar..."
    sleep 2
done

echo "✓ Ollama está rodando!"
echo ""

echo "Baixando modelo tinyllama..."
docker exec incident-ollama ollama pull tinyllama

echo ""
echo "================================================"
echo "✓ Setup concluído!"
echo "================================================"
echo ""
echo "Teste a API:"
echo "  curl http://localhost:8000/health"
echo ""
echo "Documentação:"
echo "  http://localhost:8000/docs"
echo ""
