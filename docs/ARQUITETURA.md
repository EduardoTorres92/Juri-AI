# Arquitetura do JuriAI

## Visão geral

O JuriAI é uma aplicação Django que combina gestão de escritório de advocacia com recursos de IA para análise de documentos e assistência jurídica.

## Módulos principais

### `clientes`
- **Cliente:** PF/PJ, CPF/CNPJ, telefone, status, VIP
- **Processo:** Caso/protocolo vinculado ao cliente (número, descrição, valor total)
- **Honorário:** Valores, datas, status (pendente/pago), vencimento
- **Prazo:** Prazos vinculados a cliente e processo (ex: recurso, contestação)
- **Documentos:** Upload de PDFs, OCR automático, indexação para RAG

### `ia`
- **Chat com IA:** Assistente jurídico por cliente (RAG nos documentos)
- **Chat por área:** Assistente por área de atuação
- **Análise jurídica:** Análise de petições via LangChain/OpenAI
- **RAG:** LanceDB + OpenAI Embeddings para busca semântica

### `areas`
- **Área de atuação:** Módulos (ex: Penal, Civil)
- **Documentos da área:** PDFs base para consulta via IA

### `usuarios`
- Cadastro e login
- Vinculação de clientes/processos ao usuário logado

## Fluxo de dados

### Documentos e RAG
1. Upload de documento → `Documentos` (cliente) ou `DocumentoArea` (área)
2. Signal `post_save` → tarefa assíncrona (Django-Q2)
3. OCR (Docling) → extração de texto
4. RAG → indexação no LanceDB
5. Chat usa RAG para responder com base nos documentos

### Calendário de prazos
- API `/api/prazos/` retorna JSON para FullCalendar
- Eventos: vermelho (vencido), roxo (futuro)
- Clique no evento → página do cliente

## Tecnologias por camada

| Camada | Tecnologia |
|--------|------------|
| Backend | Django 6 |
| Banco | SQLite (dev) / PostgreSQL (prod) |
| Filas | Django-Q2 |
| IA/LLM | OpenAI, LangChain, Agno |
| RAG | LanceDB, OpenAI Embeddings |
| OCR | Docling |
| Frontend | Tailwind CSS, Chart.js, FullCalendar |
