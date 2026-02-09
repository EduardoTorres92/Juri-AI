from django.contrib import admin

from .models import AreaAtuacao, DocumentoArea


@admin.register(AreaAtuacao)
class AreaAtuacaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'user')


@admin.register(DocumentoArea)
class DocumentoAreaAdmin(admin.ModelAdmin):
    list_display = ('nome_exibicao', 'tipo', 'area', 'data_upload')
