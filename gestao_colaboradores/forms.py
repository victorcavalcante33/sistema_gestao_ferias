# gestao_colaboradores/forms.py
from django import forms
from .models import Colaborador, Configuracao
import datetime

class ColaboradorForm(forms.ModelForm):
    class Meta:
        model = Colaborador
        fields = [
            'nome', 'graduacao', 'numero_re', 'data_nascimento', 'data_ultima_promocao', 'classificacao_concurso', 'data_ingresso_pm',
            'opcao1_tipo', 'opcao1_mes', 'opcao1_inicio',
            'opcao2_tipo', 'opcao2_mes', 'opcao2_inicio',
            'opcao3_tipo', 'opcao3_mes', 'opcao3_inicio',
        ]
        widgets = {
            'opcao1_mes': forms.Select(choices=Colaborador.MESES),
            'opcao2_mes': forms.Select(choices=Colaborador.MESES),
            'opcao3_mes': forms.Select(choices=Colaborador.MESES),
            'opcao1_inicio': forms.Select(choices=Colaborador.INICIO_FERIAS_CHOICES),
            'opcao2_inicio': forms.Select(choices=Colaborador.INICIO_FERIAS_CHOICES),
            'opcao3_inicio': forms.Select(choices=Colaborador.INICIO_FERIAS_CHOICES),
            'opcao1_tipo': forms.Select(choices=Colaborador.TIPO_OPCAO_CHOICES),
            'opcao2_tipo': forms.Select(choices=Colaborador.TIPO_OPCAO_CHOICES),
            'opcao3_tipo': forms.Select(choices=Colaborador.TIPO_OPCAO_CHOICES),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Verificar a consistência das opções
        for i in range(1, 4):
            opcao_tipo = cleaned_data.get(f'opcao{i}_tipo')
            opcao_mes = cleaned_data.get(f'opcao{i}_mes')
            opcao_inicio = cleaned_data.get(f'opcao{i}_inicio')
            
            # Verificar se existe algum campo preenchido para esta opção
            has_some_data = bool(opcao_tipo or opcao_mes or opcao_inicio)
            
            # Se algum campo está preenchido, todos devem estar
            if has_some_data and not (opcao_tipo and opcao_mes and opcao_inicio):
                raise forms.ValidationError(f'A Opção {i} deve ter todos os campos preenchidos ou nenhum.')
        
        # Verificar se pelo menos uma opção foi preenchida
        opcao1_completa = cleaned_data.get('opcao1_tipo') and cleaned_data.get('opcao1_mes') and cleaned_data.get('opcao1_inicio')
        opcao2_completa = cleaned_data.get('opcao2_tipo') and cleaned_data.get('opcao2_mes') and cleaned_data.get('opcao2_inicio')
        opcao3_completa = cleaned_data.get('opcao3_tipo') and cleaned_data.get('opcao3_mes') and cleaned_data.get('opcao3_inicio')
        
        if not (opcao1_completa or opcao2_completa or opcao3_completa):
            raise forms.ValidationError('Pelo menos uma opção de férias deve ser preenchida completamente.')
            
        # Verificar se não há opções duplicadas
        opcoes = []
        for i in range(1, 4):
            opcao_tipo = cleaned_data.get(f'opcao{i}_tipo')
            opcao_mes = cleaned_data.get(f'opcao{i}_mes')
            opcao_inicio = cleaned_data.get(f'opcao{i}_inicio')
            
            if opcao_tipo and opcao_mes and opcao_inicio:
                opcoes.append((opcao_tipo, opcao_mes, opcao_inicio))
        
        # Verificar duplicatas
        if len(opcoes) > len(set(opcoes)):
            raise forms.ValidationError('Não pode haver opções de férias duplicadas.')
            
        return cleaned_data

    def clean_numero_re(self):
        numero_re = self.cleaned_data.get('numero_re')
        if numero_re <= 0:
            raise forms.ValidationError('O número de RE deve ser um número positivo.')
        if len(str(numero_re)) != 6:
            raise forms.ValidationError('O número de RE deve ter exatamente 6 dígitos.')
        return numero_re
    
    def clean_data_ultima_promocao(self):
        data_ultima_promocao = self.cleaned_data.get('data_ultima_promocao')
        if data_ultima_promocao and data_ultima_promocao > datetime.date.today():
            raise forms.ValidationError('A data de promoção não pode ser no futuro.')
        return data_ultima_promocao

    def clean_classificacao_concurso(self):
        classificacao_concurso = self.cleaned_data.get('classificacao_concurso')
        if classificacao_concurso and classificacao_concurso <= 0:
            raise forms.ValidationError('A classificação no concurso deve ser um número positivo.')
        return classificacao_concurso

    def clean_data_ingresso_pm(self):
        data_ingresso_pm = self.cleaned_data.get('data_ingresso_pm')
        if data_ingresso_pm and data_ingresso_pm > datetime.date.today():
            raise forms.ValidationError('A data de ingresso na PM não pode ser no futuro.')
        return data_ingresso_pm

    def clean_data_nascimento(self):
        data_nascimento = self.cleaned_data.get('data_nascimento')
        if data_nascimento and data_nascimento > datetime.date.today():
            raise forms.ValidationError('A data de nascimento não pode ser no futuro.')
        return data_nascimento

class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = ['limite_por_mes']
        labels = {
            'limite_por_mes': 'Limite de Policiais por Mês',
        }
