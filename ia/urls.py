from django.urls import path
from . import views

urlpatterns = [
    path('chat/<int:id>/', views.chat, name='chat'),
    path('stream_response/', views.stream_resposta, name='stream_resposta'),
    path('chat_area/<int:id>/', views.chat_area, name='chat_area'),
    path('stream_resposta_area/', views.stream_resposta_area, name='stream_resposta_area'),
    path('ver_referencias_area/<int:id>/', views.ver_referencias_area, name='ver_referencias_area'),
    path('ver_referencias/<int:id>/', views.ver_referencias, name='ver_referencias'),
    path('ver_conversa/<int:id>/', views.ver_conversa, name='ver_conversa'),
    path('ver_conversa_area/<int:id>/', views.ver_conversa_area, name='ver_conversa_area'),
    path('salvar_resposta/', views.salvar_resposta, name='salvar_resposta'),
    path('analise_jurisprudencia/<int:id>/', views.analise_jurisprudencia, name='analise_jurisprudencia'),
    path('processar_analise/<int:id>/', views.processar_analise, name='processar_analise'),
    path('documento/<int:id>/status/', views.documento_status, name='documento_status'),
]
