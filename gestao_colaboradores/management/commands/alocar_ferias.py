from django.core.management.base import BaseCommand
from gestao_colaboradores.models import Colaborador, Configuracao
from django.db.models import Q
import datetime
import re

# Definiu00e7u00e3o da ordem de prioridade das graduau00e7u00f5es
PRIORIDADE_GRADUACOES = {
    'Coronel': 1,
    'Tenente-Coronel': 2,
    'Major': 3,
    'Capitu00e3o': 4,
    '1u00ba Tenente': 5,
    '2u00ba Tenente': 6,
    'Aspirante a Oficial': 7,
    'Subtenente': 8,
    '1u00ba Sargento': 9,
    '2u00ba Sargento': 10,
    '3u00ba Sargento': 11,
    'Cabo': 12,
    'Soldado': 13,
}

# Mapeamento de abreviau00e7u00f5es para meses completos
MAPA_MESES = {
    'JAN': 'Janeiro',
    'FEV': 'Fevereiro',
    'MAR': 'Maru00e7o',
    'ABR': 'Abril',
    'MAI': 'Maio',
    'JUN': 'Junho',
    'JUL': 'Julho',
    'AGO': 'Agosto',
    'SET': 'Setembro',
    'OUT': 'Outubro',
    'NOV': 'Novembro',
    'DEZ': 'Dezembro',
}

MESES = ['Janeiro', 'Fevereiro', 'Maru00e7o', 'Abril', 'Maio', 'Junho', 
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

class Command(BaseCommand):
    help = 'Aloca fu00e9rias para os policiais respeitando a hierarquia e preferu00eancias'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando alocau00e7u00e3o de fu00e9rias...'))
        
        # Obter configurau00e7u00e3o do limite por mu00eas
        configuracao = Configuracao.objects.first()
        if not configuracao:
            configuracao = Configuracao.objects.create(limite_por_mes=1)
        
        limite_por_mes = configuracao.limite_por_mes
        self.stdout.write(f"Limite por mu00eas: {limite_por_mes}")
        
        # Resetar alocau00e7u00f5es anteriores
        Colaborador.objects.all().update(
            mes_alocado=None, inicio_ferias_alocado=None,
            quinzena1_alocada=None, inicio_quinzena1_alocado=None,
            quinzena2_alocada=None, inicio_quinzena2_alocado=None,
            quinzena3_alocada=None, inicio_quinzena3_alocado=None
        )
        
        # Inicializar contador de alocau00e7u00f5es por mu00eas
        contagem_por_mes = {mes: 0 for mes in MESES}
        
        # Ordenar colaboradores por prioridade
        colaboradores = self.ordenar_por_prioridade(Colaborador.objects.all())
        self.stdout.write(f"Total de colaboradores: {len(colaboradores)}")
        
        # Fila de realocau00e7u00e3o para os que nu00e3o conseguirem suas preferu00eancias
        fila_realocacao = []
        
        # Primeira passagem: alocar preferu00eancias por ordem de prioridade
        for colaborador in colaboradores:
            self.stdout.write(f"\nProcessando {colaborador.nome} - {colaborador.graduacao} - Tipo de fu00e9rias: {colaborador.tipo_ferias}")
            preferencias = self.extrair_preferencias(colaborador)
            
            # Ordenar preferu00eancias por ordem (1u00aa, 2u00aa, 3u00aa)
            preferencias.sort(key=lambda p: p['ordem'])
            
            alocado = False
            for preferencia in preferencias:
                mes = preferencia['mes']
                self.stdout.write(f"  Tentando alocar em {mes} (preferu00eancia {preferencia['ordem']})")
                
                # Verificar se hu00e1 vaga no mu00eas
                if contagem_por_mes[mes] < limite_por_mes:
                    # Alocar o colaborador neste mu00eas
                    colaborador.mes_alocado = mes
                    colaborador.inicio_ferias_alocado = '1'  # Sempre comeu00e7a no dia 1
                    colaborador.save()
                    
                    # Incrementar a contagem do mu00eas
                    contagem_por_mes[mes] += 1
                    
                    self.stdout.write(self.style.SUCCESS(f"  ALOCADO em {mes}"))
                    alocado = True
                    break
                else:
                    self.stdout.write(f"  {mes} estu00e1 cheio ({contagem_por_mes[mes]}/{limite_por_mes})")
            
            if not alocado:
                self.stdout.write(f"  Nu00e3o foi possu00edvel alocar nas preferu00eancias. Adicionando u00e0 fila de realocau00e7u00e3o.")
                fila_realocacao.append(colaborador)
        
        # Segunda passagem: alocar os que nu00e3o conseguiram suas preferu00eancias
        self.stdout.write(f"\nProcessando fila de realocau00e7u00e3o: {len(fila_realocacao)} colaboradores")
        for colaborador in fila_realocacao:
            self.stdout.write(f"\nRealocando {colaborador.nome} - {colaborador.graduacao}")
            
            # Tentar alocar no mu00eas com menor ocupau00e7u00e3o
            mes_menos_ocupado = min(contagem_por_mes.items(), key=lambda x: x[1])[0]
            self.stdout.write(f"  Tentando alocar no mu00eas menos ocupado: {mes_menos_ocupado} ({contagem_por_mes[mes_menos_ocupado]}/{limite_por_mes})")
            
            if contagem_por_mes[mes_menos_ocupado] < limite_por_mes:
                # Alocar o colaborador neste mu00eas
                colaborador.mes_alocado = mes_menos_ocupado
                colaborador.inicio_ferias_alocado = '1'  # Sempre comeu00e7a no dia 1
                colaborador.save()
                
                # Incrementar a contagem do mu00eas
                contagem_por_mes[mes_menos_ocupado] += 1
                
                self.stdout.write(self.style.SUCCESS(f"  REALOCADO em {mes_menos_ocupado}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ERRO: Todos os meses estu00e3o cheios! Nu00e3o foi possu00edvel alocar."))
        
        # Exibir resultado da alocau00e7u00e3o
        self.stdout.write("\nResultado da alocau00e7u00e3o:")
        for mes in MESES:
            self.stdout.write(f"{mes}: {contagem_por_mes[mes]}/{limite_por_mes}")
        
        self.stdout.write(self.style.SUCCESS('\nAlocau00e7u00e3o de fu00e9rias conclu00edda com sucesso!'))
    
    def extrair_preferencias_do_nome(self, nome):
        preferencias = []
        
        # Se o nome contiver ' - ', extrair a parte antes do ' - '
        if ' - ' in nome:
            partes_nome = nome.split(' - ')[0]
        else:
            partes_nome = nome
        
        # Regex para encontrar sequu00eancias de 3 letras maiu00fasculas (abreviau00e7u00f5es dos meses)
        meses_abreviados = re.findall(r'\b[A-Z]{3}\b', partes_nome)
        
        # Para cada abreviau00e7u00e3o encontrada, converter para o nome completo do mu00eas e adicionar u00e0 lista
        for i, mes_abreviado in enumerate(meses_abreviados):
            if mes_abreviado in MAPA_MESES:
                preferencias.append({
                    'mes': MAPA_MESES[mes_abreviado],
                    'tipo': 'mensal',
                    'ordem': i + 1  # A ordem u00e9 determinada pela posiu00e7u00e3o no nome
                })
        
        return preferencias
    
    def extrair_preferencias(self, colaborador):
        # Primeiro tentar extrair do nome
        if colaborador.nome:
            preferencias_do_nome = self.extrair_preferencias_do_nome(colaborador.nome)
            if preferencias_do_nome:
                return preferencias_do_nome
        
        # Se nu00e3o encontrou preferu00eancias no nome, usar os campos individuais
        preferencias = []
        
        # Preferu00eancias mensais
        if colaborador.tipo_ferias == 'mensal':
            if colaborador.mes1_preferencia:
                preferencias.append({
                    'mes': colaborador.mes1_preferencia,
                    'tipo': 'mensal',
                    'ordem': 1
                })
            if colaborador.mes2_preferencia:
                preferencias.append({
                    'mes': colaborador.mes2_preferencia,
                    'tipo': 'mensal',
                    'ordem': 2
                })
            if colaborador.mes3_preferencia:
                preferencias.append({
                    'mes': colaborador.mes3_preferencia,
                    'tipo': 'mensal',
                    'ordem': 3
                })
        
        return preferencias
    
    def ordenar_por_prioridade(self, colaboradores):
        def get_prioridade(colaborador):
            # Utilizar a ordem da graduau00e7u00e3o (1 u00e9 maior prioridade)
            graduacao_valor = PRIORIDADE_GRADUACOES.get(colaborador.graduacao, 99)
            
            # Casos especiais para diferentes graduau00e7u00f5es
            if colaborador.graduacao == 'Soldado':
                # Para Soldados: primeiro critu00e9rio u00e9 graduau00e7u00e3o, segundo u00e9 data de ingresso, terceiro u00e9 classificau00e7u00e3o no concurso
                data_ingresso = colaborador.data_ingresso_pm or datetime.date.max
                classificacao = colaborador.classificacao_concurso or 99999
                data_nascimento = colaborador.data_nascimento or datetime.date.max
                return (graduacao_valor, data_ingresso, classificacao, data_nascimento)
            
            elif colaborador.graduacao == 'Cabo':
                # Para Cabos sem classificau00e7u00e3o no concurso: usar data de ingresso e depois idade
                data_promocao = colaborador.data_ultima_promocao or datetime.date.max
                
                # Verificar se tem classificau00e7u00e3o no concurso
                if colaborador.classificacao_concurso is None:
                    data_ingresso = colaborador.data_ingresso_pm or datetime.date.max
                    data_nascimento = colaborador.data_nascimento or datetime.date.max
                    return (graduacao_valor, data_promocao, data_ingresso, data_nascimento)
                else:
                    classificacao = colaborador.classificacao_concurso
                    return (graduacao_valor, data_promocao, classificacao)
            
            else:
                # Para todas as outras graduau00e7u00f5es: data de promou00e7u00e3o, classificau00e7u00e3o no concurso
                data_promocao = colaborador.data_ultima_promocao or datetime.date.max
                classificacao = colaborador.classificacao_concurso or 99999
                data_ingresso = colaborador.data_ingresso_pm or datetime.date.max
                data_nascimento = colaborador.data_nascimento or datetime.date.max
                return (graduacao_valor, data_promocao, classificacao, data_ingresso, data_nascimento)
        
        return sorted(colaboradores, key=get_prioridade)
