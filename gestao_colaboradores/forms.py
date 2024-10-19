# gestao_colaboradores/forms.py
from django import forms
from .models import Colaborador
import datetime

class ColaboradorForm(forms.ModelForm):
    class Meta:
        model = Colaborador
        fields = ['nome', 'graduacao', 'numero_re', 'data_promocao', 'mes1_preferencia', 'mes2_preferencia', 'mes3_preferencia']
        widgets = {
            'mes1_preferencia': forms.Select(choices=Colaborador.MESES),
            'mes2_preferencia': forms.Select(choices=Colaborador.MESES),
            'mes3_preferencia': forms.Select(choices=Colaborador.MESES),
        }

    def clean_numero_re(self):
        numero_re = self.cleaned_data.get('numero_re')
        if numero_re <= 0:
            raise forms.ValidationError('O número de RE deve ser um número positivo.')
        if len(str(numero_re)) != 6:
            raise forms.ValidationError('O número de RE deve ter exatamente 6 dígitos.')
        return numero_re
    
    def clean_data_promocao(self):
        data_promocao = self.cleaned_data.get('data_promocao')
        if data_promocao and data_promocao > datetime.date.today():
            raise forms.ValidationError('A data de promoção não pode ser no futuro.')
        return data_promocao

# gestao_colaboradores/forms.py

from .models import Configuracao

class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = ['limite_por_mes']
        labels = {
            'limite_por_mes': 'Limite de Policiais por Mês',
        }
