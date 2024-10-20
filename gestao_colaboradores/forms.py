# gestao_colaboradores/forms.py
from django import forms
from .models import Colaborador, Configuracao
import datetime

class ColaboradorForm(forms.ModelForm):
    class Meta:
        model = Colaborador
        fields = [
            'nome', 'graduacao', 'numero_re', 'data_promocao',
            'tipo_ferias', 'mes1_preferencia', 'mes2_preferencia', 'mes3_preferencia',
            'quinzena1_mes', 'quinzena2_mes'
        ]
        widgets = {
            'mes1_preferencia': forms.Select(choices=Colaborador.MESES),
            'mes2_preferencia': forms.Select(choices=Colaborador.MESES),
            'mes3_preferencia': forms.Select(choices=Colaborador.MESES),
            'quinzena1_mes': forms.Select(choices=Colaborador.MESES),
            'quinzena2_mes': forms.Select(choices=Colaborador.MESES),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        tipo_ferias = cleaned_data.get('tipo_ferias')

        if tipo_ferias == 'mensal':
            mes1 = cleaned_data.get('mes1_preferencia')
            mes2 = cleaned_data.get('mes2_preferencia')
            mes3 = cleaned_data.get('mes3_preferencia')
            if not mes1 or not mes2 or not mes3:
                raise forms.ValidationError('Todos os meses de férias devem ser preenchidos se o tipo de férias for mensal.')

        elif tipo_ferias == 'quinzenal':
            quinzena1 = cleaned_data.get('quinzena1_mes')
            quinzena2 = cleaned_data.get('quinzena2_mes')
            if not quinzena1 or not quinzena2:
                raise forms.ValidationError('Ambas as quinzenas devem ser preenchidas se o tipo de férias for quinzenal.')

            # Remover meses de preferência ao selecionar quinzenal
            cleaned_data['mes1_preferencia'] = None
            cleaned_data['mes2_preferencia'] = None
            cleaned_data['mes3_preferencia'] = None

        return cleaned_data


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

class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = ['limite_por_mes']
        labels = {
            'limite_por_mes': 'Limite de Policiais por Mês',
        }
