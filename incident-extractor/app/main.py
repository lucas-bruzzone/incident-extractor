"""API FastAPI para extração de informações de incidentes usando LLM"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.models import IncidentRequest, IncidentResponse
from app.services.llm_service import OllamaService
from app.services.preprocessor import IncidentPreprocessor

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Instâncias globais dos serviços
ollama_service: OllamaService = None
preprocessor: IncidentPreprocessor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    global ollama_service, preprocessor
    
    # Startup
    logger.info("Iniciando serviços...")
    ollama_service = OllamaService()
    preprocessor = IncidentPreprocessor()
    
    # Verifica conexão com Ollama
    if await ollama_service.health_check():
        logger.info("Conexão com Ollama estabelecida com sucesso")
    else:
        logger.warning("Não foi possível conectar ao Ollama. Verifique se o serviço está rodando.")
    
    yield
    
    # Shutdown
    logger.info("Encerrando serviços...")
    await ollama_service.close()


# Inicializa a aplicação FastAPI
app = FastAPI(
    title="Incident Information Extractor API",
    description="API para extração automática de informações estruturadas de descrições de incidentes usando LLM",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "service": "Incident Information Extractor",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Verifica o status da API e do serviço Ollama"""
    ollama_status = await ollama_service.health_check()
    
    return {
        "api_status": "healthy",
        "ollama_status": "connected" if ollama_status else "disconnected",
        "timestamp": datetime.now().isoformat()
    }


@app.post(
    "/extract-incident",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Incident Extraction"],
    summary="Extrai informações estruturadas de um incidente",
    response_description="Informações extraídas do incidente em formato JSON"
)
async def extract_incident(request: IncidentRequest):
    """
    Processa a descrição de um incidente e extrai informações estruturadas.
    
    O sistema realiza as seguintes etapas:
    1. Pré-processamento do texto (normalização, limpeza)
    2. Envio para o LLM com prompt estruturado
    3. Extração e validação do JSON retornado
    4. Retorno das informações estruturadas
    
    Args:
        request: Objeto contendo a descrição do incidente
        
    Returns:
        IncidentResponse: Informações estruturadas extraídas (data, local, tipo, impacto)
        
    Raises:
        HTTPException: Em caso de erro no processamento
    """
    try:
        logger.info(f"Recebida requisição de extração. Tamanho da descrição: {len(request.descricao)} caracteres")
        
        # Pré-processamento do texto
        processed_text, reference_date = preprocessor.preprocess(request.descricao)
        
        logger.info(f"Texto pré-processado. Data de referência: {reference_date}")
        
        # Extrai informações usando o LLM
        start_time = datetime.now()
        result = await ollama_service.extract_incident_info(
            incident_description=processed_text,
            reference_date=reference_date
        )
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Extração concluída em {processing_time:.2f} segundos")
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao processar incidente: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar o incidente: {str(e)}"
        )


@app.get("/models", tags=["LLM"])
async def list_models():
    """Lista os modelos disponíveis no Ollama"""
    try:
        url = f"{ollama_service.base_url}/api/tags"
        response = await ollama_service.client.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao listar modelos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar modelos: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
