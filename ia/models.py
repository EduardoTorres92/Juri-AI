from django.db import models

from areas.models import AreaAtuacao
from clientes.models import Cliente, Documentos


class Pergunta(models.Model):
    pergunta = models.TextField()
    resposta = models.TextField(blank=True, default='')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)

    def __str__(self):
        return self.pergunta[:50]


class PerguntaArea(models.Model):
    pergunta = models.TextField()
    resposta = models.TextField(blank=True, default='')
    area = models.ForeignKey(AreaAtuacao, on_delete=models.CASCADE)

    def __str__(self):
        return self.pergunta[:50]


class ContextRagArea(models.Model):
    content = models.JSONField()
    tool_name = models.CharField(max_length=255)
    tool_args = models.JSONField(null=True, blank=True)
    pergunta = models.ForeignKey(PerguntaArea, on_delete=models.CASCADE)

    def __str__(self):
        return self.tool_name

    def content_para_exibicao(self):
        if isinstance(self.content, str):
            return [self.content]
        if isinstance(self.content, list):
            return [str(item) if not isinstance(item, str) else item for item in self.content]
        return [str(self.content)]


class ContextRag(models.Model):
    content = models.JSONField()
    tool_name = models.CharField(max_length=255)
    tool_args = models.JSONField(null=True, blank=True)
    pergunta = models.ForeignKey(Pergunta, on_delete=models.CASCADE)

    def __str__(self):
        return self.tool_name

    def content_para_exibicao(self):
        """Retorna o conteúdo formatado para exibição no template."""
        if isinstance(self.content, str):
            return [self.content]
        if isinstance(self.content, list):
            return [str(item) if not isinstance(item, str) else item for item in self.content]
        return [str(self.content)]


class AnaliseJurisprudencia(models.Model):
    documento = models.ForeignKey(Documentos, on_delete=models.CASCADE, related_name='analises')
    indice_risco = models.IntegerField()
    classificacao = models.CharField(max_length=20)  # Baixo, Médio, Alto, Crítico
    erros_coerencia = models.JSONField(default=list)
    riscos_juridicos = models.JSONField(default=list)
    problemas_formatacao = models.JSONField(default=list)
    red_flags = models.JSONField(default=list)
    tempo_processamento = models.IntegerField(default=0)  # em segundos
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Análise - {self.documento.get_tipo_display()} - {self.data_criacao.strftime('%d/%m/%Y %H:%M')}"
