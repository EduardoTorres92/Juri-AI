# JuriAI

<p align="center">
  <strong>Painel do advogado com IA jurídica</strong>
</p>

Sistema web para escritórios de advocacia que integra gestão de clientes, processos, honorários, prazos e um assistente virtual com Inteligência Artificial para análise de documentos jurídicos.

## Funcionalidades

- **Dashboard** – Visão geral com métricas de consultas IA, casos ativos, faturamento e calendário de prazos
- **Gestão de clientes** – Cadastro, edição e listagem de clientes (PF/PJ)
- **Processos e casos** – Protocolos por cliente com número de processo e valor total
- **Honorários** – Controle de valores, datas e status (pendente/pago)
- **Prazos** – Calendário integrado com prazos vinculados a clientes e processos
- **Documentos** – Upload de PDFs, petições e contratos com OCR automático
- **Chat com IA** – Assistente jurídico com RAG nos documentos do cliente
- **Análise jurídica** – Análise de petições e documentos via IA (LangChain/OpenAI)
- **Áreas de atuação** – Módulos por área (ex: Penal, Civil) com documentos e chat especializado
- **Integração DataJud** – Consulta de processos na API pública do CNJ

## Tecnologias

- **Backend:** Django 6, Python 3.12+
- **IA:** LangChain, OpenAI, Agno, LanceDB (RAG)
- **OCR:** Docling
- **Frontend:** Tailwind CSS, Chart.js, FullCalendar
- **Filas:** Django-Q2
- **Gerenciador de pacotes:** [UV](https://docs.astral.sh/uv/)

## Requisitos

- [UV](https://docs.astral.sh/uv/) – gerenciador de pacotes Python
- Python 3.12+
- (Opcional) GPU NVIDIA para aceleração de modelos

> **Nota Windows:** Alguns pacotes CUDA (`nvidia-cufile-cu12`, `nvidia-nccl-cu12`, `nvidia-nvshmem-cu12`, `triton`) são opcionais no Windows. Em Linux com GPU, todas as dependências serão instaladas.

## Instalação

```bash
# Clone o repositório
git clone https://github.com/EduardoTorres92/Juri-AI.git
cd juri-ai

# Instale o UV (se ainda não tiver)
# Windows (PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Criar ambiente virtual e instalar dependências
uv sync

# Copiar variáveis de ambiente
cp .env.example .env
# Edite o .env com suas chaves (ver seção Variáveis de ambiente)

# Aplicar migrações
uv run python manage.py migrate

# Criar superusuário (opcional)
uv run python manage.py createsuperuser
```

## Executar o projeto

```bash
# Servidor de desenvolvimento
uv run python manage.py runserver

# Em outro terminal: worker para tarefas assíncronas (OCR, RAG)
uv run python manage.py qcluster
```

Acesse: http://127.0.0.1:8000

## Variáveis de ambiente

Configure o arquivo `.env` na raiz do projeto:

| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave secreta do Django |
| `OPENAI_API_KEY` | Chave da API OpenAI (para IA e RAG) |
| `ASAAS_API_KEY` | (Opcional) Chave da API Asaas para pagamentos |

## Estrutura do projeto

```
Juri-AI/
├── core/                 # Configurações Django
├── usuarios/             # Cadastro e autenticação
├── clientes/             # Clientes, processos, honorários, prazos
├── areas/                # Áreas de atuação e documentos
├── ia/                   # IA, chat, RAG, análise jurídica
├── modulos/              # Módulos auxiliares (ex: Asaas)
├── templates/            # Templates base e estáticos
├── manage.py
├── pyproject.toml        # Dependências (UV)
└── .env.example
```

## Documentação adicional

- [Arquitetura e módulos](docs/ARQUITETURA.md)
- [Guia de deploy](docs/DEPLOY.md)

## Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
