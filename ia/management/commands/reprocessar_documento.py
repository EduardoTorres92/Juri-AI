"""
Comando para reprocessar um documento: OCR + RAG.

Uso: uv run python manage.py reprocessar_documento <id_documento>

Útil para:
- Documentos enviados antes das correções de OCR
- Debug de problemas no pipeline
- Verificar se o conteúdo foi extraído corretamente
"""
from django.core.management.base import BaseCommand

from clientes.models import Documentos

from ia.tasks import ocr_and_markdown_file, rag_documentos


class Command(BaseCommand):
    help = "Reprocessa um documento (OCR + RAG) pelo ID"

    def add_arguments(self, parser):
        parser.add_argument("id", type=int, help="ID do documento")
        parser.add_argument("--list", action="store_true", help="Listar todos os documentos e sair")

    def handle(self, *args, **options):
        if options.get("list"):
            docs = Documentos.objects.select_related("cliente").all()
            self.stdout.write(f"\nDocumentos ({docs.count()}):\n")
            for d in docs:
                len_c = len(d.content or "")
                status = "OK" if len_c > 50 else "VAZIO/POUCO"
                self.stdout.write(f"  ID {d.id}: {d.arquivo.name} | {len_c} chars | {status} | Cliente: {d.cliente.nome}\n")
            return

        doc_id = options["id"]

        try:
            doc = Documentos.objects.get(id=doc_id)
        except Documentos.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Documento {doc_id} não encontrado."))
            return

        self.stdout.write(f"Reprocessando documento {doc_id}: {doc.arquivo.name}")
        self.stdout.write(f"  Cliente: {doc.cliente.nome} (id={doc.cliente.id})")
        self.stdout.write(f"  Arquivo: {doc.arquivo.path}")

        self.stdout.write("  Executando OCR...")
        try:
            ocr_and_markdown_file(doc_id)
            doc.refresh_from_db()
            len_content = len(doc.content or "")
            self.stdout.write(self.style.SUCCESS(f"  OCR concluído. Conteúdo extraído: {len_content} caracteres"))
            if len_content < 50:
                self.stdout.write(self.style.WARNING("  ATENÇÃO: Pouco conteúdo extraído. Verifique se o PDF tem texto ou se é escaneado."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  Erro no OCR: {e}"))
            import traceback
            traceback.print_exc()
            return

        self.stdout.write("  Inserindo no RAG...")
        try:
            rag_documentos(doc_id)
            self.stdout.write(self.style.SUCCESS("  RAG concluído com sucesso."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  Erro no RAG: {e}"))
            import traceback
            traceback.print_exc()
            return

        self.stdout.write(self.style.SUCCESS("\nDocumento reprocessado com sucesso!"))
