from django.db import models


class DadosEmpresa(models.Model):
    dados = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dados da empresa - {self.data_criacao.strftime('%d/%m/%Y')}"
