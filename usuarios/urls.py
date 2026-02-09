from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.login, name='login'),
    path('evolution-api/', views.evolution_api_config, name='evolution_api_config'),
]
