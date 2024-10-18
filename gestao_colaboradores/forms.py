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

    def clean_numero_re(self):
        numero_re = self.cleaned_data.get('numero_re')
        if Colaborador.objects.filter(numero_re=numero_re).exists():
            raise forms.ValidationError("Um colaborador com este número de RE já foi cadastrado.")
        return numero_re