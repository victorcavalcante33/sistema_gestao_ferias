from django.urls import path
from . import views

urlpatterns = [
    path('cadastrar/', views.cadastrar_colaborador, name='cadastrar_colaborador'),
    path('lista/', views.lista_colaboradores, name='lista_colaboradores'),
]
