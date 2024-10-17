from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('colaboradores/', include('gestao_colaboradores.urls')),
]