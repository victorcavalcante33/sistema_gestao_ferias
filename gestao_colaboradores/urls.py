from django.urls import path
from . import views

urlpatterns = [
    path('cadastrar/', views.cadastrar_colaborador, name='cadastrar_colaborador'),
    path('lista/', views.lista_colaboradores, name='lista_colaboradores'),
    path('alocar_ferias/', views.alocar_ferias_novo, name='alocar_ferias'),
    path('exportar_pdf/', views.exportar_pdf, name='exportar_pdf'),
    path('exportar_csv/', views.exportar_csv, name='exportar_csv'),
]
