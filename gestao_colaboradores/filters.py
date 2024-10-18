# gestao_colaboradores/filters.py
import django_filters
from django.db.models import Q
from .models import Colaborador

class ColaboradorFilter(django_filters.FilterSet):
    graduacao = django_filters.ChoiceFilter(choices=[
        ('Capitão', 'Capitão'),
        ('Tenente', 'Tenente'),
        ('Subtenente', 'Subtenente'),
        ('1º Sargento', '1º Sargento'),
        ('2º Sargento', '2º Sargento'),
        ('3º Sargento', '3º Sargento'),
        ('Cabo', 'Cabo'),
        ('Soldado', 'Soldado'),
    ], label='Graduação')

    numero_re = django_filters.NumberFilter(label='Número de RE')

    data_promocao = django_filters.DateFilter(
        field_name='data_promocao', lookup_expr='exact', label='Data da Última Promoção')

    mes_alocado = django_filters.CharFilter(
        method='filter_by_mes_preferencia', label='Mês de Férias Alocado')

    def filter_by_mes_preferencia(self, queryset, name, value):
        # Filtro para buscar colaboradores cujas preferências incluem o mês alocado
        return queryset.filter(
            Q(mes1_preferencia=value) | Q(mes2_preferencia=value) | Q(mes3_preferencia=value)
        )

    class Meta:
        model = Colaborador
        fields = ['graduacao', 'numero_re', 'data_promocao']
