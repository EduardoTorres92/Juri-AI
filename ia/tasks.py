import logging

from django.shortcuts import get_object_or_404

from clientes.models import Documentos

from areas.models import DocumentoArea

from .agents import JuriAI

logger = logging.getLogger(__name__)


def _get_pdf_converter_with_ocr():
    """Retorna DocumentConverter com OCR habilitado para PDFs (incluindo escaneados)."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    # force_full_page_ocr=False usa detecção híbrida (mais estável)
    pipeline_options.ocr_options = RapidOcrOptions(force_full_page_ocr=False)

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )


def _extract_text_pypdfium2(file_path):
    """Fallback: extrai texto com pypdfium2 (PDFs com texto embutido, sem ML)."""
    import pypdfium2 as pdfium

    parts = []
    with pdfium.PdfDocument(file_path) as pdf:
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            try:
                parts.append(textpage.get_text_range())
            finally:
                textpage.close()
    return "\n\n".join(parts)


def ocr_and_markdown_file(instance_id):
    from pathlib import Path

    from docling.document_converter import DocumentConverter

    documentos = get_object_or_404(Documentos, id=instance_id)
    file_path = Path(documentos.arquivo.path)

    if not file_path.exists():
        logger.error("Arquivo não encontrado: %s", file_path)
        return

    texto = ""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        # 1. Tenta pypdfium2 primeiro (rápido, sem ML, PDFs com texto)
        try:
            texto = _extract_text_pypdfium2(file_path)
        except Exception as e:
            logger.warning("pypdfium2 falhou: %s", e)

        # 2. Se vazio, tenta Docling padrão
        if len(texto.strip()) < 50:
            try:
                converter = DocumentConverter()
                result = converter.convert(file_path)
                doc = result.document
                texto = doc.export_to_markdown() or ""
            except Exception as e:
                logger.warning("Docling padrão falhou: %s", e)

        # 3. Se ainda vazio, tenta com OCR (PDFs escaneados)
        if len(texto.strip()) < 50:
            try:
                converter = _get_pdf_converter_with_ocr()
                result = converter.convert(file_path)
                doc = result.document
                texto = doc.export_to_markdown() or ""
            except Exception as e:
                logger.exception("OCR falhou para documento %s: %s", instance_id, e)
    else:
        # Outros formatos: Docling
        try:
            converter = DocumentConverter()
            result = converter.convert(file_path)
            doc = result.document
            texto = doc.export_to_markdown() or ""
        except Exception as e:
            logger.exception("Conversão falhou para documento %s: %s", instance_id, e)

    documentos.content = texto
    documentos.save()


def rag_documentos(instance_id):
    documentos = get_object_or_404(Documentos, id=instance_id)
    if not documentos.content or not documentos.content.strip():
        logger.warning("Documento %s sem conteúdo para indexar no RAG.", instance_id)
        return
    try:
        JuriAI.get_knowledge().insert(
            name=documentos.arquivo.name,
            text_content=documentos.content,
            metadata={
                "cliente_id": documentos.cliente.id,
                "name": documentos.arquivo.name,
            },
        )
    except Exception as e:
        logger.exception("Erro ao indexar documento %s no RAG: %s", instance_id, e)


def ocr_documento_area(instance_id):
    """OCR para DocumentoArea (códigos, minutas, jurisprudência)."""
    from pathlib import Path

    from docling.document_converter import DocumentConverter

    doc = get_object_or_404(DocumentoArea, id=instance_id)
    file_path = Path(doc.arquivo.path)

    if not file_path.exists():
        logger.error("Arquivo não encontrado: %s", file_path)
        return

    texto = ""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        try:
            texto = _extract_text_pypdfium2(file_path)
        except Exception as e:
            logger.warning("pypdfium2 falhou: %s", e)

        if len(texto.strip()) < 50:
            try:
                converter = DocumentConverter()
                result = converter.convert(file_path)
                doc_obj = result.document
                texto = doc_obj.export_to_markdown() or ""
            except Exception as e:
                logger.warning("Docling padrão falhou: %s", e)

        if len(texto.strip()) < 50:
            try:
                converter = _get_pdf_converter_with_ocr()
                result = converter.convert(file_path)
                doc_obj = result.document
                texto = doc_obj.export_to_markdown() or ""
            except Exception as e:
                logger.exception("OCR falhou para documento área %s: %s", instance_id, e)
    else:
        try:
            converter = DocumentConverter()
            result = converter.convert(file_path)
            doc_obj = result.document
            texto = doc_obj.export_to_markdown() or ""
        except Exception as e:
            logger.exception("Conversão falhou para documento área %s: %s", instance_id, e)

    doc.content = texto
    doc.save()


def rag_documento_area(instance_id):
    """Indexa DocumentoArea no RAG com metadata area_id e user_id."""
    doc = get_object_or_404(DocumentoArea, id=instance_id)
    if not doc.content or not doc.content.strip():
        logger.warning("Documento área %s sem conteúdo para indexar no RAG.", instance_id)
        return
    try:
        JuriAI.get_knowledge().insert(
            name=doc.arquivo.name,
            text_content=doc.content,
            metadata={
                "area_id": doc.area.id,
                "user_id": doc.area.user_id,
                "tipo": doc.tipo,
                "name": doc.arquivo.name,
            },
        )
    except Exception as e:
        logger.exception("Erro ao indexar documento área %s no RAG: %s", instance_id, e)


def rag_dados_empresa(instance_id):
    ...
