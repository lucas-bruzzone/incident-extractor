"""Templates de prompt para extracao de informacoes de incidentes"""

INCIDENT_EXTRACTION_PROMPT = """Você é um assistente especializado em extrair informações estruturadas de descrições de incidentes.

Analise a descrição do incidente e extraia as seguintes informações em formato JSON:
- data_ocorrencia: data e hora do incidente no formato YYYY-MM-DD HH:MM (se mencionada)
- local: local onde o incidente ocorreu
- tipo_incidente: tipo ou categoria do incidente
- impacto: descrição breve do impacto causado

REGRAS CRÍTICAS:
1. Retorne APENAS um objeto JSON válido
2. Não adicione texto antes ou depois do JSON
3. Não adicione explicações
4. Use aspas duplas para strings
5. Se a informação não estiver presente, use null
6. Não quebre linhas dentro dos valores de string
7. O formato deve ser exatamente: {{"chave": "valor", "chave2": "valor2"}}

EXEMPLOS:

Entrada: "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
Data de referência: 2025-02-04
Saída:
{{"data_ocorrencia": "2025-02-03 14:00", "local": "São Paulo", "tipo_incidente": "Falha no servidor", "impacto": "Sistema de faturamento indisponível por 2 horas"}}

Entrada: "Hoje pela manhã, houve uma queda de energia no data center de Brasília afetando todos os serviços críticos."
Data de referência: 2025-02-04
Saída:
{{"data_ocorrencia": "2025-02-04 09:00", "local": "Brasília", "tipo_incidente": "Queda de energia", "impacto": "Todos os serviços críticos afetados"}}

Entrada: "Vazamento de dados no banco de clientes detectado pela equipe de segurança."
Data de referência: 2025-02-04
Saída:
{{"data_ocorrencia": null, "local": null, "tipo_incidente": "Vazamento de dados", "impacto": "Banco de clientes comprometido"}}

Entrada: "No dia 27/01 às 15h30, na filial de Campinas, ocorreu um ataque de ransomware que criptografou 500GB de arquivos críticos."
Data de referência: 2025-02-04
Saída:
{{"data_ocorrencia": "2025-01-27 15:30", "local": "Campinas", "tipo_incidente": "Ataque de ransomware", "impacto": "500GB de arquivos críticos criptografados"}}

Agora processe a seguinte descrição e retorne APENAS o JSON:

Descrição: {incident_description}
Data de referência: {reference_date}

JSON:"""


def build_extraction_prompt(incident_description: str, reference_date: str) -> str:
    """
    Constrói o prompt completo para extração de informações

    Args:
        incident_description: Descrição do incidente (já pré-processada)
        reference_date: Data de referência no formato YYYY-MM-DD

    Returns:
        Prompt formatado pronto para envio ao LLM
    """
    return INCIDENT_EXTRACTION_PROMPT.format(
        incident_description=incident_description, reference_date=reference_date
    )
