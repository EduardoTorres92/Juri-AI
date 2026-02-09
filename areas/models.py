import os

from django.contrib.auth.models import User
from django.db import models
from martor.models import MartorField


class AreaAtuacao(models.Model):
    """Área de atuação do advogado (ex: Processo Penal, Direito Civil)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, default='')

    def __str__(self):
        return self.nome


class DocumentoArea(models.Model):
    """Documentos da área (códigos, minutas, etc) para consulta via RAG."""
    TIPO_CHOICES = [
        ('CODIGO', 'Código / Lei'),
        ('MINUTA', 'Minuta'),
        ('JURISPRUDENCIA', 'Jurisprudência'),
        ('OUTRO', 'Outro'),
    ]
    area = models.ForeignKey(AreaAtuacao, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255, blank=True, default='')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='OUTRO')
    arquivo = models.FileField(upload_to='documentos_area/')
    data_upload = models.DateTimeField(auto_now_add=True)
    content = MartorField(blank=True, default='')

    def __str__(self):
        return self.nome_exibicao

    @property
    def nome_exibicao(self):
        if self.nome and self.nome.strip():
            return self.nome.strip()
        return os.path.basename(self.arquivo.name) if self.arquivo else ''
