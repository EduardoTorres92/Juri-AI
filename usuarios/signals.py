import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

from areas.models import DocumentoArea
from clientes.models import Documentos

from ia.tasks import ocr_and_markdown_file, ocr_documento_area, rag_documento_area, rag_documentos

logger = logging.getLogger(__name__)


def _processar_documento_background(documento_id):
    """Executa OCR e RAG em background para não bloquear/bloquear o servidor."""
    try:
        ocr_and_markdown_file(documento_id)
        rag_documentos(documento_id)
    except Exception as e:
        logger.exception("Erro ao processar documento %s em background: %s", documento_id, e)


@receiver(post_save, sender=Documentos)
def post_save_documentos(sender, instance, created, **kwargs):
    if created:
        # Executa em thread separada para não bloquear a requisição e evitar encerrar o servidor
        thread = threading.Thread(
            target=_processar_documento_background,
            args=(instance.id,),
            daemon=True,
        )
        thread.start()


def _processar_documento_area_background(documento_id):
    """Executa OCR e RAG em background para DocumentoArea."""
    try:
        ocr_documento_area(documento_id)
        rag_documento_area(documento_id)
    except Exception as e:
        logger.exception("Erro ao processar documento área %s em background: %s", documento_id, e)


@receiver(post_save, sender=DocumentoArea)
def post_save_documento_area(sender, instance, created, **kwargs):
    if created:
        thread = threading.Thread(
            target=_processar_documento_area_background,
            args=(instance.id,),
            daemon=True,
        )
        thread.start()
