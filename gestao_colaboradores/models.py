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

    nome = models.CharField(max_length=255)
    graduacao = models.CharField(max_length=20, choices=GRADUACOES)
    numero_re = models.CharField(max_length=6, unique=True)
    data_promocao = models.DateField(null=True, blank=True)

    mes1_preferencia = models.CharField(max_length=20, choices=MESES)
    mes2_preferencia = models.CharField(max_length=20, choices=MESES)
    mes3_preferencia = models.CharField(max_length=20, choices=MESES)

    def __str__(self):
        return f"{self.nome} - {self.graduacao}"