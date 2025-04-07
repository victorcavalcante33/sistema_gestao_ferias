# gestao_colaboradores/models.py
from django.db import models

class Colaborador(models.Model):
    GRADUACOES = [
        ('Coronel', 'Coronel'),
        ('Tenente-Coronel', 'Tenente-Coronel'),
        ('Major', 'Major'),
        ('Capitão', 'Capitão'),
        ('1º Tenente', '1º Tenente'),
        ('2º Tenente', '2º Tenente'),
        ('Asp Oficial', 'Asp Oficial'),
        ('Subtenente', 'Subtenente'),
        ('1º Sargento', '1º Sargento'),
        ('2º Sargento', '2º Sargento'),
        ('3º Sargento', '3º Sargento'),
        ('Cabo', 'Cabo'),
        ('Soldado', 'Soldado')
    ]

    MESES = [
        ('Janeiro', 'Janeiro'),
        ('Fevereiro', 'Fevereiro'),
        ('Março', 'Março'),
        ('Abril', 'Abril'),
        ('Maio', 'Maio'),
        ('Junho', 'Junho'),
        ('Julho', 'Julho'),
        ('Agosto', 'Agosto'),
        ('Setembro', 'Setembro'),
        ('Outubro', 'Outubro'),
        ('Novembro', 'Novembro'),
        ('Dezembro', 'Dezembro')
    ]
    
    TIPO_FERIAS_CHOICES = [
        ('mensal', 'Mensal'),
        ('quinzenal', 'Quinzenal'),
    ]

    INICIO_FERIAS_CHOICES = [
        ('1', 'Dia 1'),
        ('15', 'Dia 15'),
    ]
    
    TIPO_OPCAO_CHOICES = [
        ('mensal', 'Mensal'),
        ('quinzenal', 'Quinzenal'),
    ]

    tipo_ferias = models.CharField(max_length=20, choices=TIPO_FERIAS_CHOICES, default='mensal') 

    nome = models.CharField(max_length=255)
    graduacao = models.CharField(max_length=20, choices=GRADUACOES)
    numero_re = models.IntegerField(unique=True)
    data_ultima_promocao = models.DateField(null=True, blank=True)
    classificacao_concurso = models.IntegerField(null=True, blank=True)
    data_ingresso_pm = models.DateField(null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    
    # Campos para as opções de férias (podem ser mensais ou quinzenais)
    # Opção 1
    opcao1_tipo = models.CharField(max_length=20, choices=TIPO_OPCAO_CHOICES, null=True, blank=True)
    opcao1_mes = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    opcao1_inicio = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    
    # Opção 2
    opcao2_tipo = models.CharField(max_length=20, choices=TIPO_OPCAO_CHOICES, null=True, blank=True)
    opcao2_mes = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    opcao2_inicio = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    
    # Opção 3
    opcao3_tipo = models.CharField(max_length=20, choices=TIPO_OPCAO_CHOICES, null=True, blank=True)
    opcao3_mes = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    opcao3_inicio = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    
    # Campo para indicar alocação provisória
    alocacao_provisoria = models.BooleanField(default=False)

    # Opção 1 de férias - Campos Legados
    mes1_preferencia = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_ferias1 = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    
    # Opção 2 de férias - Campos Legados
    mes2_preferencia = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_ferias2 = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    
    # Opção 3 de férias - Campos Legados
    mes3_preferencia = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_ferias3 = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    
    # Férias quinzenais
    quinzena1_mes = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_quinzena1 = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    quinzena2_mes = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_quinzena2 = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    quinzena3_mes = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_quinzena3 = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    
    # Mês efetivamente alocado para as férias
    mes_alocado = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_ferias_alocado = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    
    # Para férias quinzenais alocadas
    quinzena1_alocada = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_quinzena1_alocado = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    quinzena2_alocada = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_quinzena2_alocado = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)
    quinzena3_alocada = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    inicio_quinzena3_alocado = models.CharField(max_length=2, choices=INICIO_FERIAS_CHOICES, null=True, blank=True)

    # Campo para armazenar as preferências originais para realocação futura
    preferencias_originais = models.TextField(null=True, blank=True)
    
    # Campo para indicar se o colaborador precisa ser realocado após remanejamento
    precisa_realocar = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nome} - {self.graduacao}"

class Configuracao(models.Model):
    limite_por_mes = models.PositiveIntegerField(default=13)

    def __str__(self):
        return f"Configurações do Sistema"
