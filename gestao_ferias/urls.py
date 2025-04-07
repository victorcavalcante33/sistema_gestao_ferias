from django.contrib import admin
from django.urls import path, include
from gestao_colaboradores import views  # Importando a view criada


urlpatterns = [
    path('exportar/pdf/', views.exportar_pdf, name='exportar_pdf'),
    path('exportar/csv/', views.exportar_csv, name='exportar_csv'), 
    path('admin/', admin.site.urls),
    path('colaboradores/', include('gestao_colaboradores.urls'),
                          
                                   ),
    
    # Define a URL raiz para a página inicial
    path('', views.pagina_inicial, name='pagina_inicial'),
]
