from django.contrib import admin

from .models import Cliente, Documentos, Honorario, Processo


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'cpf_cnpj', 'telefone', 'tipo', 'status', 'vip', 'user')


@admin.register(Documentos)
class DocumentosAdmin(admin.ModelAdmin):
    list_display = ('nome_exibicao', 'tipo', 'cliente', 'data_upload')


@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'numero_processo', 'descricao', 'valor_total', 'user')


@admin.register(Honorario)
class HonorarioAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'processo', 'valor', 'descricao', 'data', 'data_vencimento', 'status', 'user')
    list_filter = ('status', 'data')
