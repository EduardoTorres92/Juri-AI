import os

from django.contrib.auth.models import User
from django.db import models
from martor.models import MartorField


class Cliente(models.Model):
    TIPO_CHOICES = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]
    nome = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    cpf_cnpj = models.CharField(max_length=20, blank=True, default='')
    telefone = models.CharField(max_length=25, blank=True, default='')
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default='PF')
    status = models.BooleanField(default=True)
    vip = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome

    def cpf_cnpj_mascarado(self):
        """Retorna CPF ou CNPJ mascarado para exibição."""
        v = (self.cpf_cnpj or '').replace('.', '').replace('-', '').replace('/', '')
        if len(v) == 11:  # CPF
            return f"CPF ***.{v[-3:]}-{v[-2:]}" if v else ''
        if len(v) >= 14:  # CNPJ
            return f"CNPJ ***.{v[-7:][:4]}/{v[-4:]}" if v else ''
        return self.cpf_cnpj or ''


class Documentos(models.Model):
    TIPO_CHOICES = [
        ('C', 'Contrato'),
        ('P', 'Petição'),
        ('CONT', 'Contestação'),
        ('R', 'Recursos'),
        ('O', 'Outro'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255, blank=True, default='')
    tipo = models.CharField(max_length=255, choices=TIPO_CHOICES, default='O')
    arquivo = models.FileField(upload_to='documentos/')
    data_upload = models.DateTimeField(auto_now_add=True)
    content = MartorField(blank=True, default='')

    def __str__(self):
        return self.nome_exibicao

    @property
    def nome_exibicao(self):
        """Retorna o nome customizado ou o nome do arquivo."""
        if self.nome and self.nome.strip():
            return self.nome.strip()
        return os.path.basename(self.arquivo.name) if self.arquivo else ''


class Processo(models.Model):
    """Processo/caso jurídico com valor total a receber."""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    numero_processo = models.CharField(max_length=100, blank=True, default='')
    descricao = models.CharField(max_length=255, blank=True, default='')
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, help_text='Valor total do processo a receber')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        n = self.numero_processo or '—'
        return f"{self.cliente.nome} - {n} - R$ {self.valor_total}"


class Honorario(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    processo = models.ForeignKey(
        Processo, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Processo associado (opcional)'
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True, default='')
    data = models.DateField()
    data_vencimento = models.DateField(
        null=True, blank=True,
        help_text='Data de vencimento do boleto (para identificar boletos em atraso)'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.cliente.nome} - R$ {self.valor}"

    @property
    def em_atraso(self):
        """Indica se o boleto está em atraso (vencido e não pago)."""
        from django.utils import timezone
        if self.status != 'pendente':
            return False
        return self.data_vencimento and self.data_vencimento < timezone.now().date()


class Prazo(models.Model):
    """Prazo/deadline vinculado ao cliente e opcionalmente ao processo."""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    processo = models.ForeignKey(
        Processo, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Processo associado (opcional)'
    )
    data = models.DateField(help_text='Data do prazo')
    descricao = models.CharField(max_length=255, help_text='Ex: prazo para recurso, contestação')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['data', 'id']

    def __str__(self):
        proc = f' - {self.processo}' if self.processo else ''
        return f'{self.data} - {self.descricao} ({self.cliente.nome}{proc})'

    @property
    def em_atraso(self):
        from django.utils import timezone
        return self.data < timezone.now().date()
