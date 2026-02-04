"""API FastAPI para extracao de informacoes de incidentes usando LLM"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.models import IncidentRequest, IncidentResponse
from app.services.llm_service import OllamaService
from app.services.preprocessor import IncidentPreprocessor
from app.exceptions import (
    IncidentExtractorError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMResponseError,
    JSONParsingError,
    PreprocessingError,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

ollama_service: OllamaService = None
preprocessor: IncidentPreprocessor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicacao"""
    global ollama_service, preprocessor

    logger.info("Iniciando servicos...")
    ollama_service = OllamaService()
    preprocessor = IncidentPreprocessor()

    if await ollama_service.health_check():
        logger.info("Conexao com Ollama estabelecida com sucesso")
    else:
        logger.warning(
            "Nao foi possivel conectar ao Ollama. Verifique se o servico esta rodando."
        )

    yield

    logger.info("Encerrando servicos...")
    await ollama_service.close()


app = FastAPI(
    title="Incident Information Extractor API",
    description="API para extracao automatica de informacoes estruturadas de descricoes de incidentes usando LLM",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(LLMConnectionError)
async def llm_connection_error_handler(request: Request, exc: LLMConnectionError):
    """Handler para erros de conexão com LLM"""
    logger.error(f"LLMConnectionError: {exc.message} | Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "llm_connection_error",
            "message": exc.message,
            "details": exc.details,
            "suggestion": "Verifique se o serviço Ollama está rodando e acessível",
        },
    )


@app.exception_handler(LLMTimeoutError)
async def llm_timeout_error_handler(request: Request, exc: LLMTimeoutError):
    """Handler para timeout do LLM"""
    logger.error(f"LLMTimeoutError: {exc.message} | Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={
            "error": "llm_timeout_error",
            "message": exc.message,
            "details": exc.details,
            "suggestion": "O modelo pode estar carregando. Tente novamente em alguns segundos",
        },
    )


@app.exception_handler(JSONParsingError)
async def json_parsing_error_handler(request: Request, exc: JSONParsingError):
    """Handler para erros de parsing JSON"""
    logger.error(f"JSONParsingError: {exc.message} | Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "json_parsing_error",
            "message": exc.message,
            "details": exc.details,
            "suggestion": "O LLM não retornou JSON válido. Tente reformular a descrição do incidente",
        },
    )


@app.exception_handler(LLMResponseError)
async def llm_response_error_handler(request: Request, exc: LLMResponseError):
    """Handler para erros de resposta do LLM"""
    logger.error(f"LLMResponseError: {exc.message} | Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "llm_response_error",
            "message": exc.message,
            "details": exc.details,
            "suggestion": "Erro na comunicação com o LLM. Tente novamente",
        },
    )


@app.exception_handler(PreprocessingError)
async def preprocessing_error_handler(request: Request, exc: PreprocessingError):
    """Handler para erros de pré-processamento"""
    logger.error(f"PreprocessingError: {exc.message} | Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "preprocessing_error",
            "message": exc.message,
            "details": exc.details,
            "suggestion": "Verifique o formato do texto enviado",
        },
    )


@app.exception_handler(IncidentExtractorError)
async def incident_extractor_error_handler(
    request: Request, exc: IncidentExtractorError
):
    """Handler genérico para erros da aplicação"""
    logger.error(f"IncidentExtractorError: {exc.message} | Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.get("/", tags=["Health"])
async def root():
    """Endpoint raiz com informacoes da API"""
    return {
        "service": "Incident Information Extractor",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Verifica o status da API e do servico Ollama"""
    ollama_status = await ollama_service.health_check()

    return {
        "api_status": "healthy",
        "ollama_status": "connected" if ollama_status else "disconnected",
        "ollama_url": ollama_service.base_url,
        "model": ollama_service.model,
        "timestamp": datetime.now().isoformat(),
    }


@app.post(
    "/extract-incident",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Incident Extraction"],
    summary="Extrai informacoes estruturadas de um incidente",
    response_description="Informacoes extraidas do incidente em formato JSON",
    responses={
        400: {"description": "Erro no pré-processamento do texto"},
        422: {"description": "JSON inválido na resposta do LLM ou validação falhou"},
        502: {"description": "Erro de conexão ou resposta do LLM"},
        504: {"description": "Timeout na comunicação com o LLM"},
    },
)
async def extract_incident(request: IncidentRequest):
    """
    Processa a descricao de um incidente e extrai informacoes estruturadas.

    O texto é pré-processado e enviado ao LLM para extração de:
    - Data/hora do incidente
    - Local
    - Tipo de incidente
    - Impacto

    Campos não identificados são retornados como null.
    """
    logger.info(
        f"Recebida requisicao de extracao. Tamanho da descricao: {len(request.descricao)} caracteres"
    )

    try:
        processed_text, reference_date = preprocessor.preprocess(request.descricao)
    except Exception as e:
        raise PreprocessingError(
            message="Falha ao pré-processar o texto do incidente", details=str(e)
        )

    logger.info(f"Texto pre-processado. Data de referencia: {reference_date}")

    start_time = datetime.now()

    # Exceções do LLM são propagadas e tratadas pelos handlers
    result = await ollama_service.extract_incident_info(
        incident_description=processed_text, reference_date=reference_date
    )

    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    logger.info(f"Extracao concluida em {processing_time:.2f} segundos")

    return result


@app.get("/models", tags=["LLM"])
async def list_models():
    """Lista os modelos disponiveis no Ollama"""
    try:
        url = f"{ollama_service.base_url}/api/tags"
        response = await ollama_service.client.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao listar modelos: {str(e)}")
        raise LLMConnectionError(
            message="Não foi possível listar modelos do Ollama", details=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
