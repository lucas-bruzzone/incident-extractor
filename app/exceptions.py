"""Exceções customizadas para a API de extração de incidentes"""


class IncidentExtractorError(Exception):
    """Exceção base para erros da aplicação"""

    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class LLMConnectionError(IncidentExtractorError):
    """Erro de conexão com o serviço Ollama"""

    def __init__(
        self,
        message: str = "Não foi possível conectar ao serviço LLM",
        details: str = None,
    ):
        super().__init__(message, details)


class LLMTimeoutError(IncidentExtractorError):
    """Timeout na comunicação com o LLM"""

    def __init__(
        self,
        message: str = "Timeout na comunicação com o serviço LLM",
        details: str = None,
    ):
        super().__init__(message, details)


class LLMResponseError(IncidentExtractorError):
    """Resposta inválida ou malformada do LLM"""

    def __init__(self, message: str = "Resposta inválida do LLM", details: str = None):
        super().__init__(message, details)


class JSONParsingError(LLMResponseError):
    """Erro ao parsear JSON da resposta do LLM"""

    def __init__(
        self,
        message: str = "Não foi possível extrair JSON válido da resposta",
        details: str = None,
    ):
        super().__init__(message, details)


class PreprocessingError(IncidentExtractorError):
    """Erro no pré-processamento do texto"""

    def __init__(
        self,
        message: str = "Erro ao pré-processar o texto do incidente",
        details: str = None,
    ):
        super().__init__(message, details)
