# gestao_colaboradores/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('ferias/', views.lista_colaboradores, name='lista_colaboradores'),
    path('cadastrar/', views.cadastrar_colaborador, name='cadastrar_colaborador'),
]
