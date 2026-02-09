from django.urls import path
from django.shortcuts import render


def em_breve(request):
    return render(request, 'modulos/em_breve.html', {
        'titulo': 'Módulos',
        'descricao': 'Esta funcionalidade estará disponível em breve.',
    })


urlpatterns = [
    path('', em_breve),
]
