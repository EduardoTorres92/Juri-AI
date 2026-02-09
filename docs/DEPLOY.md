# Guia de Deploy

## Produção

### Configurações recomendadas

1. **`DEBUG = False`** em `core/settings.py`
2. **`SECRET_KEY`** via variável de ambiente
3. **`ALLOWED_HOSTS`** com o domínio real
4. **Banco de dados:** PostgreSQL em vez de SQLite
5. **Servidor:** Gunicorn + Nginx ou similar
6. **Static/Media:** Servir arquivos estáticos com Nginx ou CDN

### Variáveis de ambiente (produção)

```env
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=seudominio.com
DATABASE_URL=postgresql://...
OPENAI_API_KEY=...
```

### Comandos pós-deploy

```bash
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
uv run python manage.py qcluster  # Worker em background
```

### Django-Q2

O worker `qcluster` é necessário para:
- OCR de documentos
- Indexação RAG
- Outras tarefas assíncronas

Execute como serviço (systemd, supervisor, etc.) ou em processo separado.
