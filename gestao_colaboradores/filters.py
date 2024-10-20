# gestao_colaboradores/filters.py
import django_filters
from .models import Colaborador

class ColaboradorFilter(django_filters.FilterSet):
    graduacao = django_filters.ChoiceFilter(
        choices=Colaborador.GRADUACOES, label='Graduação'
    )
    numero_re = django_filters.NumberFilter(
        label='Número de RE'
    )
    data_promocao = django_filters.DateFilter(
        field_name='data_promocao', lookup_expr='exact', label='Data da Última Promoção'
    )
    mes_alocado = django_filters.ChoiceFilter(
        choices=Colaborador.MESES, label='Mês de Férias Alocado'
    )
    tipo_ferias = django_filters.ChoiceFilter(
        choices=Colaborador.TIPO_FERIAS_CHOICES, label='Tipo de Férias'
    )

    class Meta:
        model = Colaborador
        fields = ['graduacao', 'numero_re', 'data_promocao', 'mes_alocado', 'tipo_ferias']
