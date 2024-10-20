# gestao_colaboradores/models.py
from django.db import models

class Colaborador(models.Model):
    GRADUACOES = [
        ('Capitão', 'Capitão'),
        ('Tenente', 'Tenente'),
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
    tipo_ferias = models.CharField(max_length=20, choices=TIPO_FERIAS_CHOICES, default='mensal') 

    nome = models.CharField(max_length=255)
    graduacao = models.CharField(max_length=20, choices=GRADUACOES)
    numero_re = models.IntegerField(unique=True)
    data_promocao = models.DateField(null=True, blank=True)
    mes1_preferencia = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    mes2_preferencia = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    mes3_preferencia = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    mes_alocado = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    
    # Novas propriedades para gerenciamento de férias quinzenais
    quinzena1_mes = models.CharField(max_length=20, choices=MESES, null=True, blank=True)
    quinzena2_mes = models.CharField(max_length=20, choices=MESES, null=True, blank=True)

    def __str__(self):
        return f"{self.nome} - {self.graduacao}"

class Configuracao(models.Model):
    limite_por_mes = models.PositiveIntegerField(default=13)

    def __str__(self):
        return f"Configurações do Sistema"
