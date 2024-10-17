# gestao_colaboradores/forms.py
from django import forms
from .models import Colaborador

class ColaboradorForm(forms.ModelForm):
    class Meta:
        model = Colaborador
        fields = ['nome', 'graduacao', 'numero_re', 'data_promocao', 'mes1_preferencia', 'mes2_preferencia', 'mes3_preferencia']
        widgets = {
            'mes1_preferencia': forms.Select(choices=Colaborador.MESES),
            'mes2_preferencia': forms.Select(choices=Colaborador.MESES),
            'mes3_preferencia': forms.Select(choices=Colaborador.MESES),
        }
