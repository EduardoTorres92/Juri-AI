from django.contrib import admin
from .models import Pergunta, PerguntaArea, ContextRag, ContextRagArea


@admin.register(ContextRag)
class ContextRagAdmin(admin.ModelAdmin):
    list_display = ('id', 'tool_name', 'pergunta')
    list_filter = ('tool_name',)
    search_fields = ('tool_name',)


admin.site.register(Pergunta)
admin.site.register(PerguntaArea)
admin.site.register(ContextRagArea)