"""Templates de prompt para extracao de informacoes de incidentes"""

INCIDENT_EXTRACTION_PROMPT = """You are an assistant specialized in extracting structured information from incident descriptions.

Analyze the incident description and extract the following information in JSON format:
- data_ocorrencia: date and time of the incident in YYYY-MM-DD HH:MM format (if mentioned)
- local: location where the incident occurred
- tipo_incidente: type or category of the incident
- impacto: brief description of the impact caused

CRITICAL RULES:
1. Return ONLY a valid JSON object
2. Do not add any text before or after the JSON
3. Do not add explanations
4. Use double quotes for strings
5. If information is not present, use null
6. Do not break lines inside string values
7. Format must be exactly: {{"key": "value", "key2": "value2"}}

EXAMPLES:

Input: "Ontem as 14h, no escritorio de Sao Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
Reference date: 2025-02-04
Output:
{{"data_ocorrencia": "2025-02-03 14:00", "local": "Sao Paulo", "tipo_incidente": "Falha no servidor", "impacto": "Sistema de faturamento indisponivel por 2 horas"}}

Input: "Hoje pela manha, houve uma queda de energia no data center de Brasilia afetando todos os servicos criticos."
Reference date: 2025-02-04
Output:
{{"data_ocorrencia": "2025-02-04 09:00", "local": "Brasilia", "tipo_incidente": "Queda de energia", "impacto": "Todos os servicos criticos afetados"}}

Input: "Vazamento de dados no banco de clientes detectado pela equipe de seguranca."
Reference date: 2025-02-04
Output:
{{"data_ocorrencia": null, "local": null, "tipo_incidente": "Vazamento de dados", "impacto": "Banco de clientes comprometido"}}

Now process the following description and return ONLY the JSON:

Description: {incident_description}
Reference date: {reference_date}

JSON:"""


def build_extraction_prompt(incident_description: str, reference_date: str) -> str:
    """
    Constroi o prompt completo para extracao de informacoes
    """
    return INCIDENT_EXTRACTION_PROMPT.format(
        incident_description=incident_description,
        reference_date=reference_date
    )
