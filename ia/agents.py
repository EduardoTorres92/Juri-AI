import json
import os
import urllib3

import requests

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.tools import tool
from agno.vectordb.lancedb import LanceDb

from .literals import TribunalLiteral

# Suprime aviso ao desabilitar verificação SSL (DataJud pode ter certificado não reconhecido no Windows)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@tool
def search_datajud_api(tribunal: TribunalLiteral, process_number: str) -> str:
    """
    Busca informações de um processo judicial na API pública do DataJud (CNJ).

    Realiza uma consulta na API pública do Conselho Nacional de Justiça
    para obter dados de um processo judicial específico em um determinado tribunal.

    Args:
        tribunal: Código do tribunal onde o processo está tramitando.
            Valores aceitos: "tst", "tse", "stj", "stm", "trf1"-"trf6",
            "tjsp", "tjmg", etc. (ver TribunalLiteral para lista completa).
        process_number: Número do processo judicial no formato CNJ
            (ex: "00008323520184013202").

    Returns:
        Resposta da API em formato JSON como string contendo os dados do processo,
        incluindo informações como número, partes, movimentações, decisões, etc.
        Retorna JSON com campo "error" em caso de falha na requisição.
    """
    url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search"
    payload = {
        "query": {
            "match": {
                "numeroProcesso": process_number
            }
        }
    }
    headers = {
        "Authorization": f"APIKey {os.getenv('DATAJUD_API_KEY', 'cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==')}",
        "Content-Type": "application/json"
    }

    try:
        # verify=False: DataJud pode ter certificado SSL não reconhecido em alguns ambientes (ex: Windows)
        response = requests.post(
            url, headers=headers, json=payload, timeout=30, verify=False
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


class JuriAI:

    DATAJUD_BASE_URL = "https://api-publica.datajud.cnj.jus.br"
    DATAJUD_API_KEY = os.getenv('DATAJUD_API_KEY', 'cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==')
    VECTOR_DB_TABLE = "documentos"
    VECTOR_DB_URI = "lancedb"
    MEMORY_DB_FILE = "db.sqlite3"
    MEMORY_TABLE = "my_memory_table"
    AGENT_NAME = "Assistente Jurídico Virtual"
    AGENT_DESCRIPTION = (
        "Assistente virtual especializado em questões jurídicas com acesso "
        "a base de conhecimento e consulta de processos judiciais."
    )

    INSTRUCTIONS = """
    SUAS CAPACIDADES:
    1. Acesso a Base de Conhecimento (RAG): Você possui acesso a uma base de dados
       e deve usá-la para responder as perguntas do usuário de forma precisa e fundamentada.
    2. Consulta de Processos: Você pode buscar informações sobre processos judiciais
       através da API do DataJud (CNJ).

    DIRETRIZES:
    - Sempre priorize informações da base de conhecimento quando disponíveis.
    - Ao consultar processos, forneça informações claras e organizadas.
    - Se não tiver certeza sobre alguma informação, indique isso ao usuário.
    - Mantenha um tom profissional e objetivo em todas as respostas.
    """

    _knowledge = None

    @classmethod
    def get_knowledge(cls):
        if cls._knowledge is None:
            cls._knowledge = Knowledge(
                vector_db=LanceDb(
                    table_name=cls.VECTOR_DB_TABLE,
                    uri=cls.VECTOR_DB_URI,
                    embedder=OpenAIEmbedder()
                ),
            )
        return cls._knowledge

    INSTRUCTIONS_AREA = """
    SUAS CAPACIDADES:
    Você possui acesso EXCLUSIVO aos documentos anexados à área de atuação.
    Sua base de conhecimento contém códigos, leis, minutas, jurisprudência e outros materiais.

    REGRAS OBRIGATÓRIAS:
    1. Responda APENAS com base nos documentos indexados nesta área. Não invente nem especule.
    2. Sempre cite a fonte: informe de qual documento, lei, artigo, parágrafo ou inciso a informação foi extraída.
    3. Use formato como: "De acordo com o art. X do [nome do documento]...", "Conforme o inciso Y do § Z...".
    4. Se a informação não estiver nos documentos, diga claramente: "Não encontrei essa informação nos documentos da área."
    5. Mantenha tom profissional e objetivo. Não use DataJud ou fontes externas.
    """

    @classmethod
    def build_agent(cls, knowledge_filters: dict = None) -> Agent:
        if knowledge_filters is None:
            knowledge_filters = {}

        db = SqliteDb(
            db_file=cls.MEMORY_DB_FILE,
            memory_table=cls.MEMORY_TABLE
        )

        return Agent(
            name=cls.AGENT_NAME,
            description=cls.AGENT_DESCRIPTION,
            tools=[search_datajud_api],
            instructions=cls.INSTRUCTIONS,
            db=db,
            update_memory_on_run=True,
            knowledge=cls.get_knowledge(),
            knowledge_filters=knowledge_filters,
            search_knowledge=True,
        )

    @classmethod
    def build_agent_area(cls, knowledge_filters: dict = None) -> Agent:
        """Agente restrito aos documentos da área, sem DataJud, com citação obrigatória de fontes."""
        if knowledge_filters is None:
            knowledge_filters = {}

        db = SqliteDb(
            db_file=cls.MEMORY_DB_FILE,
            memory_table=cls.MEMORY_TABLE
        )

        return Agent(
            name="Assistente da Área de Atuação",
            description="Assistente que responde apenas com base nos documentos da área, sempre citando fontes.",
            tools=[],  # Sem DataJud
            instructions=cls.INSTRUCTIONS_AREA,
            db=db,
            update_memory_on_run=True,
            knowledge=cls.get_knowledge(),
            knowledge_filters=knowledge_filters,
            search_knowledge=True,
        )
