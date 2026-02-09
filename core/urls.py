"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from areas.views import (
    areas_list, area_detail, area_editar,
    documento_area_excluir, documento_area_renomear, documento_area_status,
)
from clientes.views import (
    clientes, cliente, cliente_editar, dashboard,
    documento_excluir, documento_renomear,
    processo_criar, processo_editar, processo_excluir,
    honorario_criar, honorario_editar, honorario_excluir,
    prazo_criar, prazo_criar_geral, prazo_editar, prazo_excluir, prazos_api,
)
from usuarios.views import cadastro, login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('cadastro/', cadastro, name='cadastro'),
    path('login/', login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', dashboard, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('clientes/', clientes, name='clientes'),
    path('cliente/<int:id>/', cliente, name='cliente'),
    path('cliente/<int:id>/editar/', cliente_editar, name='cliente_editar'),
    path('documento/<int:id>/excluir/', documento_excluir, name='documento_excluir'),
    path('documento/<int:id>/renomear/', documento_renomear, name='documento_renomear'),
    path('cliente/<int:cliente_id>/processo/novo/', processo_criar, name='processo_criar'),
    path('processo/<int:id>/editar/', processo_editar, name='processo_editar'),
    path('processo/<int:id>/excluir/', processo_excluir, name='processo_excluir'),
    path('cliente/<int:cliente_id>/honorario/novo/', honorario_criar, name='honorario_criar'),
    path('honorario/<int:id>/editar/', honorario_editar, name='honorario_editar'),
    path('honorario/<int:id>/excluir/', honorario_excluir, name='honorario_excluir'),
    path('cliente/<int:cliente_id>/prazo/novo/', prazo_criar, name='prazo_criar'),
    path('prazo/novo/', prazo_criar_geral, name='prazo_criar_geral'),
    path('prazo/<int:id>/editar/', prazo_editar, name='prazo_editar'),
    path('prazo/<int:id>/excluir/', prazo_excluir, name='prazo_excluir'),
    path('api/prazos/', prazos_api, name='prazos_api'),
    path('areas/', areas_list, name='areas_list'),
    path('area/<int:id>/', area_detail, name='area_detail'),
    path('area/<int:id>/editar/', area_editar, name='area_editar'),
    path('documento_area/<int:id>/excluir/', documento_area_excluir, name='documento_area_excluir'),
    path('documento_area/<int:id>/renomear/', documento_area_renomear, name='documento_area_renomear'),
    path('documento_area/<int:id>/status/', documento_area_status, name='documento_area_status'),
    path('ia/', include('ia.urls')),
    path('modulos/', include('modulos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
