Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Setup Inicial - Incident Extractor" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verificando se Ollama está rodando..." -ForegroundColor Yellow
do {
    $response = $null
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -ErrorAction SilentlyContinue
    } catch {}
    
    if ($null -eq $response) {
        Write-Host "Aguardando Ollama iniciar..."
        Start-Sleep -Seconds 2
    }
} while ($null -eq $response)

Write-Host "✓ Ollama está rodando!" -ForegroundColor Green
Write-Host ""

Write-Host "Baixando modelo tinyllama..." -ForegroundColor Yellow
docker exec incident-ollama ollama pull tinyllama

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "✓ Setup concluído!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Teste a API:" -ForegroundColor Yellow
Write-Host "  curl http://localhost:8000/health"
Write-Host ""
Write-Host "Documentação:" -ForegroundColor Yellow
Write-Host "  http://localhost:8000/docs"
Write-Host ""
