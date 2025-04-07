from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .models import Colaborador, Configuracao
from .forms import ColaboradorForm, ConfiguracaoForm
from .filters import ColaboradorFilter
import csv
import json
import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import date
import logging
import re

# Função para ordenar colaboradores por prioridade
def ordenar_por_prioridade(colaboradores):
    def get_prioridade(colaborador):
        # Utilizar a ordem da graduação (1 é maior prioridade)
        graduacao_valor = PRIORIDADE_GRADUACOES.get(colaborador.graduacao, 99)
        
        # Casos especiais para diferentes graduações
        if colaborador.graduacao == 'Soldado':
            # Para Soldados: primeiro critério é graduação, segundo é data de ingresso, terceiro é classificação no concurso
            data_ingresso = colaborador.data_ingresso_pm or datetime.date.max
            classificacao = colaborador.classificacao_concurso or 99999
            data_nascimento = colaborador.data_nascimento or datetime.date.max
            return (graduacao_valor, data_ingresso, classificacao, data_nascimento)
        
        elif colaborador.graduacao == 'Cabo':
            # Para Cabos sem classificação no concurso: usar data de ingresso e depois idade
            data_promocao = colaborador.data_ultima_promocao or datetime.date.max
            
            # Verificar se tem classificação no concurso
            if colaborador.classificacao_concurso is None:
                data_ingresso = colaborador.data_ingresso_pm or datetime.date.max
                data_nascimento = colaborador.data_nascimento or datetime.date.max
                return (graduacao_valor, data_promocao, data_ingresso, data_nascimento)
            else:
                classificacao = colaborador.classificacao_concurso
                return (graduacao_valor, data_promocao, classificacao)
        
        else:
            # Para todas as outras graduações: data de promoção, classificação no concurso
            data_promocao = colaborador.data_ultima_promocao or datetime.date.max
            classificacao = colaborador.classificacao_concurso or 99999
            data_ingresso = colaborador.data_ingresso_pm or datetime.date.max
            data_nascimento = colaborador.data_nascimento or datetime.date.max
            return (graduacao_valor, data_promocao, classificacao, data_ingresso, data_nascimento)
    
    return sorted(colaboradores, key=get_prioridade)

# Mapeamento de abreviações para meses completos
MES_ABREV = {
    'JAN': 'Janeiro',
    'FEV': 'Fevereiro',
    'MAR': 'Março',
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

# Definir as prioridades de graduação
PRIORIDADE_GRADUACOES = {
    'Coronel': 1,
    'Tenente-Coronel': 2,
    'Major': 3,
    'Capitão': 4,
    '1º Tenente': 5,
    '2º Tenente': 6,
    'Asp Oficial': 7,
    'Subtenente': 8,
    '1º Sargento': 9,
    '2º Sargento': 10,
    '3º Sargento': 11,
    'Cabo': 12,
    'Soldado': 13,
}

MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
]

# Função auxiliar para tentar alocar férias mensais
def tentar_alocar_ferias_mensais(colaborador, mes, inicio, alocacoes_por_mes, limite_por_mes, meses_limite_atingido):
    # Verificar se o mês está com limite atingido
    if mes in meses_limite_atingido:
        return None
    
    # Verificar se há vagas no mês
    if alocacoes_por_mes[mes]['vagas_disponiveis'] > 0:
        # Atualizar alocação do colaborador
        colaborador.mes_alocado = mes
        colaborador.inicio_ferias_alocado = inicio
        colaborador.save()
        
        # Atualizar contagem
        alocacoes_por_mes[mes]['vagas_disponiveis'] -= 1
        
        # Verificar se o limite foi atingido
        if alocacoes_por_mes[mes]['vagas_disponiveis'] <= 0:
            meses_limite_atingido.add(mes)
        
        # Retornar informações sobre alocação
        return {
            'mes': mes,
            'inicio': inicio,
            'tipo': 'mensal'
        }
    
    return None

# Função para verificar se é possível remanejar policiais de menor prioridade
def verificar_e_remanejar_vagas_mensais(colaborador, mes, inicio, alocacoes_por_mes, limite_por_mes, meses_limite_atingido):
    # Verificar disponibilidade em ambas as quinzenas
    chave_primeira_quinzena = 'dia_1' if inicio == '1' else 'dia_16'
    chave_segunda_quinzena = 'dia_16' if inicio == '1' else 'dia_1'  # Quinzena seguinte
    
    # Verificar se há colaboradores com prioridade menor nas quinzenas desejadas
    remaneja_quinzena1 = pode_remanejar_quinzena(colaborador, mes, chave_primeira_quinzena, alocacoes_por_mes)
    remaneja_quinzena2 = pode_remanejar_quinzena(colaborador, mes, chave_segunda_quinzena, alocacoes_por_mes)
    
    # Se for possível remanejar em ambas as quinzenas
    if remaneja_quinzena1 and remaneja_quinzena2:
        # Fazer o remanejamento nas duas quinzenas
        remanejar_quinzena(colaborador, mes, chave_primeira_quinzena, alocacoes_por_mes)
        remanejar_quinzena(colaborador, mes, chave_segunda_quinzena, alocacoes_por_mes)
        
        # Adicionar colaborador às listas de alocações para cada quinzena
        alocacoes_por_mes[mes][chave_primeira_quinzena]['colaboradores'].append({
            'colaborador': colaborador,
            'tipo': 'mensal',
            'quinzena_complementar': chave_segunda_quinzena
        })
        
        alocacoes_por_mes[mes][chave_segunda_quinzena]['colaboradores'].append({
            'colaborador': colaborador,
            'tipo': 'mensal',
            'quinzena_complementar': chave_primeira_quinzena
        })
        
        # Verificar se a quinzena atingiu o limite
        if alocacoes_por_mes[mes][chave_primeira_quinzena]['vagas_disponiveis'] <= 0:
            quinzena = "Primeira" if chave_primeira_quinzena == 'dia_1' else "Segunda"
            meses_limite_atingido.add(f"{mes} ({quinzena} Quinzena)")
        
        if alocacoes_por_mes[mes][chave_segunda_quinzena]['vagas_disponiveis'] <= 0:
            quinzena = "Primeira" if chave_segunda_quinzena == 'dia_1' else "Segunda"
            meses_limite_atingido.add(f"{mes} ({quinzena} Quinzena)")
        
        return {'mes': mes, 'inicio': inicio}
    
    # Se não há vagas disponíveis, verificar se podemos remanejar alguém com menor prioridade
    return verificar_e_remanejar_vagas_mensais(colaborador, mes, inicio, alocacoes_por_mes, limite_por_mes, meses_limite_atingido)

# Função para verificar se é possível remanejar alguém em uma quinzena
def pode_remanejar_quinzena(colaborador_novo, mes, chave_quinzena, alocacoes_por_mes):
    # Se ainda há vagas disponíveis, não é necessário remanejar
    if alocacoes_por_mes[mes][chave_quinzena]['vagas_disponiveis'] > 0:
        return True
    
    # Verificar a graduação do novo colaborador
    grad_novo = colaborador_novo.graduacao
    prioridade_novo = PRIORIDADE_GRADUACOES.get(grad_novo, 99)
    
    # Verificar se há algum colaborador com menor prioridade
    for alocacao in alocacoes_por_mes[mes][chave_quinzena]['colaboradores']:
        colaborador_atual = alocacao['colaborador']
        grad_atual = colaborador_atual.graduacao
        prioridade_atual = PRIORIDADE_GRADUACOES.get(grad_atual, 99)
        
        # Se encontrarmos algum com menor prioridade, podemos remanejar
        if prioridade_atual > prioridade_novo:
            return True
    
    # Não encontramos candidatos para remanejamento
    return False

# Função para remanejar colaboradores com menor prioridade em uma quinzena
def remanejar_quinzena(colaborador_novo, mes, chave_quinzena, alocacoes_por_mes):
    # Se ainda há vagas disponíveis, não é necessário remanejar
    if alocacoes_por_mes[mes][chave_quinzena]['vagas_disponiveis'] > 0:
        alocacoes_por_mes[mes][chave_quinzena]['vagas_disponiveis'] -= 1
        return True
    
    # Verificar a graduação do novo colaborador
    grad_novo = colaborador_novo.graduacao
    prioridade_novo = PRIORIDADE_GRADUACOES.get(grad_novo, 99)
    
    # Encontrar o colaborador com menor prioridade
    menor_prioridade = None
    indice_menor_prioridade = -1
    
    for idx, alocacao in enumerate(alocacoes_por_mes[mes][chave_quinzena]['colaboradores']):
        colaborador_atual = alocacao['colaborador']
        grad_atual = colaborador_atual.graduacao
        prioridade_atual = PRIORIDADE_GRADUACOES.get(grad_atual, 99)
        
        if prioridade_atual > prioridade_novo:
            if menor_prioridade is None or prioridade_atual > menor_prioridade[1]:
                menor_prioridade = (colaborador_atual, prioridade_atual, idx)
                indice_menor_prioridade = idx
    
    # Se encontrou um colaborador com menor prioridade
    if menor_prioridade:
        # Remover a alocação do colaborador com menor prioridade
        colaborador_remover = menor_prioridade[0]
        alocacao_remover = alocacoes_por_mes[mes][chave_quinzena]['colaboradores'].pop(indice_menor_prioridade)
        
        # Se for alocação mensal, remover também da outra quinzena
        if alocacao_remover['tipo'] == 'mensal':
            quinzena_complementar = alocacao_remover['quinzena_complementar']
            
            # Encontrar e remover da outra quinzena
            for idx, aloc in enumerate(alocacoes_por_mes[mes][quinzena_complementar]['colaboradores']):
                if aloc['colaborador'] == colaborador_remover:
                    alocacoes_por_mes[mes][quinzena_complementar]['colaboradores'].pop(idx)
                    alocacoes_por_mes[mes][quinzena_complementar]['vagas_disponiveis'] += 1
                    break
        
        # Marcar o colaborador para ser realocado posteriormente
        colaborador_remover.precisa_realocar = True
        colaborador_remover.save()
        
        return True
    
    return False

# Função auxiliar para tentar alocar uma quinzena
def tentar_alocar_quinzena(colaborador, mes, inicio, alocacoes_por_mes, limite_por_mes, meses_limite_atingido, quinzena):
    if not mes or not inicio:
        return None
    
    chave_quinzena = 'dia_1' if inicio == '1' else 'dia_16'
    
    # Verificar se há espaço disponível para a quinzena
    if alocacoes_por_mes[mes][chave_quinzena]['vagas_disponiveis'] > 0:
        # Registrar alocação
        alocacoes_por_mes[mes][chave_quinzena]['vagas_disponiveis'] -= 1
        
        # Adicionar colaborador à lista de alocações
        alocacoes_por_mes[mes][chave_quinzena]['colaboradores'].append({
            'colaborador': colaborador,
            'tipo': 'quinzenal',
            'quinzena': quinzena
        })
        
        # Verificar se a quinzena atingiu o limite
        if alocacoes_por_mes[mes][chave_quinzena]['vagas_disponiveis'] <= 0:
            descricao = "Primeira" if chave_quinzena == 'dia_1' else "Segunda"
            meses_limite_atingido.add(f"{mes} ({descricao} Quinzena)")
        
        return {'mes': mes, 'inicio': inicio}
    
    # Se não há vagas disponíveis, verificar se podemos remanejar alguém com menor prioridade
    return verificar_e_remanejar_vagas_quinzenais(colaborador, mes, inicio, alocacoes_por_mes, limite_por_mes, meses_limite_atingido, quinzena)

# Função para verificar se é possível remanejar policiais de menor prioridade
def verificar_e_remanejar_vagas_quinzenais(colaborador, mes, inicio, alocacoes_por_mes, limite_por_mes, meses_limite_atingido, quinzena):
    # Verificar disponibilidade
    chave_quinzena = 'dia_1' if inicio == '1' else 'dia_16'
    
    # Verificar se há colaboradores com prioridade menor na quinzena desejada
    remaneja_quinzena = pode_remanejar_quinzena(colaborador, mes, chave_quinzena, alocacoes_por_mes)
    
    # Se for possível remanejar
    if remaneja_quinzena:
        # Fazer o remanejamento
        remanejar_quinzena(colaborador, mes, chave_quinzena, alocacoes_por_mes)
        
        # Adicionar colaborador à lista de alocações
        alocacoes_por_mes[mes][chave_quinzena]['colaboradores'].append({
            'colaborador': colaborador,
            'tipo': 'quinzenal',
            'quinzena': quinzena
        })
        
        return {'mes': mes, 'inicio': inicio}
    
    return None

# Função para encontrar o mês com menor ocupação
def encontrar_mes_menos_ocupado(alocacoes_por_mes, tipo_ferias):
    if tipo_ferias == 'mensal':
        # Para férias mensais, precisamos encontrar mês com disponibilidade em ambas quinzenas
        return min(MESES, key=lambda m: max(alocacoes_por_mes[m]['dia_1']['vagas_disponiveis'], alocacoes_por_mes[m]['dia_16']['vagas_disponiveis']))
    else:
        # Para férias quinzenais, podemos procurar quinzenas específicas
        ocupacao_quinzenas = []
        for mes in MESES:
            ocupacao_quinzenas.append((mes, 'dia_1', alocacoes_por_mes[mes]['dia_1']['vagas_disponiveis']))
            ocupacao_quinzenas.append((mes, 'dia_16', alocacoes_por_mes[mes]['dia_16']['vagas_disponiveis']))
        
        mes_dia, tipo_dia, _ = min(ocupacao_quinzenas, key=lambda x: x[2])
        return mes_dia

# Função para encontrar o segundo mês com menor ocupação (para segunda quinzena)
def encontrar_segundo_mes_menos_ocupado(alocacoes_por_mes, primeiro_mes):
    mes_ocupacao = [(mes, max(alocacoes_por_mes[mes]['dia_1']['vagas_disponiveis'], alocacoes_por_mes[mes]['dia_16']['vagas_disponiveis'])) 
                  for mes in MESES if mes != primeiro_mes]
    return min(mes_ocupacao, key=lambda x: x[1])[0]

def alocar_ferias(colaboradores, limite_por_mes):
    # Dicionário para rastrear alocações
    alocados_por_quinzena = {
        (mes, quinzena): [] for mes in MESES 
        for quinzena in ['Q1', 'Q2']
    }
    
    # Contadores de capacidade
    contagem_quinzenal = {
        (mes, quinzena): 0 for mes in MESES 
        for quinzena in ['Q1', 'Q2']
    }
    
    # Ordenar por prioridade
    colaboradores_ordenados = ordenar_por_prioridade(colaboradores)
    fila_realocacao = []
    
    # DEBUG: Mostrar ordem de prioridade dos colaboradores
    print("Ordem de prioridade dos colaboradores:")
    for idx, colaborador in enumerate(colaboradores_ordenados):
        print(f"{idx+1}. {colaborador.nome} - {colaborador.graduacao}")
        preferencias_mensais, _ = extrair_preferencias_do_colaborador(colaborador)
        for p in preferencias_mensais:
            print(f"   - Preferência {p['ordem']}: {p['mes']}")
    
    def tentar_alocar_mensal(colaborador, mes):
        nonlocal contagem_quinzenal, alocados_por_quinzena
        
        # Imprimir o que estamos tentando fazer
        print(f"Tentando alocar {colaborador.nome} no mês {mes}")
        
        # Verificar capacidade em ambas as quinzenas
        q1_cheio = contagem_quinzenal[(mes, 'Q1')] >= limite_por_mes
        q2_cheio = contagem_quinzenal[(mes, 'Q2')] >= limite_por_mes
        
        if not q1_cheio and not q2_cheio:
            # Alocar normalmente
            contagem_quinzenal[(mes, 'Q1')] += 1
            contagem_quinzenal[(mes, 'Q2')] += 1
            alocados_por_quinzena[(mes, 'Q1')].append(colaborador)
            alocados_por_quinzena[(mes, 'Q2')].append(colaborador)
            colaborador.mes_alocado = mes
            colaborador.tipo_alocacao = 'Mensal'
            # Mostrar que conseguimos alocar
            print(f"SUCESSO: {colaborador.nome} alocado em {mes}")
            return True
        else:
            print(f"O mês {mes} está cheio: Q1={q1_cheio}, Q2={q2_cheio}")
        
        # Verificar se podemos desalojar alguém
        candidatos_desalojar = []
        
        # Encontrar os ocupantes de menor prioridade
        for quinzena in ['Q1', 'Q2']:
            ocupantes = alocados_por_quinzena[(mes, quinzena)]
            for ocupante in ocupantes:
                # Verificar a prioridade baseada na graduação
                grad_ocupante = ocupante.graduacao
                grad_colaborador = colaborador.graduacao
                
                prioridade_ocupante = PRIORIDADE_GRADUACOES.get(grad_ocupante, 99)
                prioridade_colaborador = PRIORIDADE_GRADUACOES.get(grad_colaborador, 99)
                
                if prioridade_ocupante > prioridade_colaborador:  # Menor valor = maior prioridade
                    if ocupante not in candidatos_desalojar:
                        candidatos_desalojar.append(ocupante)
                        print(f"Candidato a desalojar: {ocupante.nome} - {ocupante.graduacao}")
        
        # Ordenar candidatos por prioridade (menor prioridade primeiro)
        candidatos_desalojar.sort(key=lambda x: PRIORIDADE_GRADUACOES.get(x.graduacao, 99), reverse=True)
        
        # Verificar se temos pelo menos 2 candidatos para desalojar ou se temos vagas suficientes
        if len(candidatos_desalojar) >= 2 or (len(candidatos_desalojar) == 1 and (not q1_cheio or not q2_cheio)):
            # Desalojar os candidatos necessários
            for desalojado in candidatos_desalojar:
                # Remover das quinzenas
                for quinzena in ['Q1', 'Q2']:
                    if desalojado in alocados_por_quinzena[(mes, quinzena)]:
                        alocados_por_quinzena[(mes, quinzena)].remove(desalojado)
                        contagem_quinzenal[(mes, quinzena)] -= 1
                
                # Resetar alocação do desalojado
                desalojado.mes_alocado = None
                desalojado.tipo_alocacao = None
                desalojado.inicio_ferias_alocado = None
                fila_realocacao.append(desalojado)
                print(f"DESALOJADO: {desalojado.nome} para abrir vaga para {colaborador.nome}")
            
            # Alocar o novo colaborador
            contagem_quinzenal[(mes, 'Q1')] += 1
            contagem_quinzenal[(mes, 'Q2')] += 1
            alocados_por_quinzena[(mes, 'Q1')].append(colaborador)
            alocados_por_quinzena[(mes, 'Q2')].append(colaborador)
            colaborador.mes_alocado = mes
            colaborador.inicio_ferias_alocado = '1'  # Primeiro dia do mês
            colaborador.tipo_alocacao = 'Mensal'
            print(f"SUCESSO via desalojamento: {colaborador.nome} alocado em {mes}")
            return True
        
        print(f"Não foi possível alocar {colaborador.nome} em {mes}")
        return False

    # Primeira passagem - tentar alocar preferências
    for colaborador in colaboradores_ordenados:
        alocado = False
        print(f"\nProcessando {colaborador.nome} - {colaborador.graduacao}")
        
        # Extrair preferências do colaborador usando a função melhorada
        preferencias_mensais, preferencias_quinzenais = extrair_preferencias_do_colaborador(colaborador)
        
        # Processar preferências mensais em ordem
        if colaborador.tipo_ferias == 'mensal' and preferencias_mensais:
            # Ordenar as preferências por ordem (1ª, 2ª, 3ª opção)
            preferencias_mensais = sorted(preferencias_mensais, key=lambda p: p.get('ordem', 999))
            
            # Mostrar as preferências que estamos tentando
            print(f"Preferências de {colaborador.nome}:")
            for p in preferencias_mensais:
                print(f"  - Preferência {p['ordem']}: {p['mes']}")
            
            for preferencia in preferencias_mensais:
                print(f"Tentando preferência {preferencia['ordem']}: {preferencia['mes']}")
                alocado = tentar_alocar_mensal(colaborador, preferencia['mes'])
                if alocado:
                    break
        
        # Processar preferências quinzenais se não conseguiu alocar mensal
        if not alocado and preferencias_quinzenais:
            # Implementar lógica para alocação quinzenal aqui
            pass
        
        if not alocado:
            print(f"Adicionando {colaborador.nome} à fila de realocação")
            fila_realocacao.append(colaborador)
    
    # Segunda passagem - realocar os que não conseguiram
    print(f"\nProcessando fila de realocação: {len(fila_realocacao)} colaboradores")
    while fila_realocacao:
        colaborador = fila_realocacao.pop(0)
        alocado = False
        print(f"\nRealocando {colaborador.nome} - {colaborador.graduacao}")
        
        # Primeiro tentar NOVAMENTE as preferências originais do colaborador
        # pois elas podem ter se tornado disponíveis após desalojamentos
        preferencias_mensais, preferencias_quinzenais = extrair_preferencias_do_colaborador(colaborador)
        
        # Tentar alocar nas preferências na ordem correta
        if colaborador.tipo_ferias == 'mensal' and preferencias_mensais:
            # Ordenar as preferências por ordem (1ª, 2ª, 3ª opção)
            preferencias_mensais = sorted(preferencias_mensais, key=lambda p: p.get('ordem', 999))
            
            for preferencia in preferencias_mensais:
                print(f"Tentando alocar {colaborador.nome} em {preferencia['mes']} (ordem: {preferencia.get('ordem', 'N/A')})")
                if tentar_alocar_mensal(colaborador, preferencia['mes']):
                    alocado = True
                    break
        
        # Se não conseguiu em nenhuma preferência, tentar qualquer mês disponível
        if not alocado:
            print(f"Tentando alocar {colaborador.nome} em qualquer mês disponível")
            # Tentar alocar em qualquer mês com vagas
            for mes in MESES:
                if tentar_alocar_mensal(colaborador, mes):
                    alocado = True
                    break
        
        # Se ainda não conseguiu, alocar no mês com menor ocupação
        if not alocado:
            mes_menos_ocupado = min(
                MESES, 
                key=lambda m: sum(contagem_quinzenal[(m, q)] for q in ['Q1', 'Q2'])
            )
            print(f"Tentando alocar {colaborador.nome} no mês menos ocupado: {mes_menos_ocupado}")
            tentar_alocar_mensal(colaborador, mes_menos_ocupado)
    
    return colaboradores

def exportar_pdf(request):
    colaboradores_filtrados = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all()).qs
    
    # Chamar a função de alocação caso ainda não tenha sido feita
    configuracao, _ = Configuracao.objects.get_or_create(id=1)
    limite_por_mes = configuracao.limite_por_mes
    
    # Verificar se há alocação
    tem_alocacao = any([
        c.mes_alocado is not None or 
        c.quinzena1_alocada is not None
        for c in Colaborador.objects.all()[:5]
    ])
    
    if not tem_alocacao:
        colaboradores = alocar_ferias(Colaborador.objects.all(), limite_por_mes)
        # Salvar as alocações
        for colaborador in colaboradores:
            colaborador.save()
        # Recalcular counts_per_month
        counts_per_month = {mes: 0 for mes in MESES}
        for colab in Colaborador.objects.all():
            if colab.mes_alocado:
                counts_per_month[colab.mes_alocado] += 1
            if colab.quinzena1_alocada:
                counts_per_month[colab.quinzena1_alocada] += 0.5
            if colab.quinzena2_alocada:
                counts_per_month[colab.quinzena2_alocada] += 0.5
            if colab.quinzena3_alocada:
                counts_per_month[colab.quinzena3_alocada] += 0.5
    
    # Refresh the list of collaborators from the database
    colaboradores_filtrados = colaborador_filter.qs
    
    # Aplicar filtros adicionais se necessário
    if request.GET.get('nome', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(nome__icontains=request.GET.get('nome'))
    if request.GET.get('re', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(re=request.GET.get('re'))
    if request.GET.get('posto', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(posto=request.GET.get('posto'))
    
    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]
    
    # Colaboradores ordenados por critérios de prioridade
    colaboradores_ordenados = ordenar_por_prioridade(colaboradores_filtrados)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="colaboradores.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, altura - 50, "Lista dos Efetivos")

    y = altura - 80
    p.setFont("Helvetica", 12)
    for colaborador in colaboradores_filtrados:
        p.drawString(50, y, f"Nome: {colaborador.nome}")
        y -= 20
        p.drawString(50, y, f"Graduacao: {colaborador.graduacao}")
        y -= 20
        p.drawString(50, y, f"Numero de RE: {colaborador.numero_re}")
        y -= 20
        data_ultima_promocao = colaborador.data_ultima_promocao.strftime('%d/%m/%Y') if colaborador.data_ultima_promocao else 'Nao informada'
        p.drawString(50, y, f"Data da Ultima Promocao: {data_ultima_promocao}")
        y -= 20
        classificacao = str(colaborador.classificacao_concurso) if colaborador.classificacao_concurso else 'Nao informada'
        p.drawString(50, y, f"Classificacao no Concurso: {classificacao}")
        y -= 20
        data_ingresso = colaborador.data_ingresso_pm.strftime('%d/%m/%Y') if colaborador.data_ingresso_pm else 'Nao informada'
        p.drawString(50, y, f"Data de Ingresso na PM: {data_ingresso}")
        y -= 20
        
        # Exibir informações sobre alocação de férias
        if colaborador.tipo_ferias == 'mensal' and colaborador.mes_alocado:
            p.drawString(50, y, f"Mes Alocado: {colaborador.mes_alocado}")
        elif colaborador.quinzena1_alocada:
            p.drawString(50, y, f"Quinzena Alocada: {colaborador.quinzena1_alocada}")
        else:
            p.drawString(50, y, "Ferias nao alocadas")
        
        y -= 30

        if y < 50:
            p.showPage()
            y = altura - 50
            p.setFont("Helvetica", 12)

    p.save()
    return response

# Função para exportar CSV
def exportar_csv(request):
    colaborador_filter = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all())
    colaboradores_filtrados = colaborador_filter.qs
    
    # Verificar se há alocação
    configuracao, _ = Configuracao.objects.get_or_create(id=1)
    limite_por_mes = configuracao.limite_por_mes
    
    tem_alocacao = any([
        c.mes_alocado is not None or 
        c.quinzena1_alocada is not None
        for c in Colaborador.objects.all()[:5]
    ])
    
    if not tem_alocacao:
        colaboradores = alocar_ferias(Colaborador.objects.all(), limite_por_mes)
        # Salvar as alocações
        for colaborador in colaboradores:
            colaborador.save()
        # Recalcular counts_per_month
        counts_per_month = {mes: 0 for mes in MESES}
        for colab in Colaborador.objects.all():
            if colab.mes_alocado:
                counts_per_month[colab.mes_alocado] += 1
            if colab.quinzena1_alocada:
                counts_per_month[colab.quinzena1_alocada] += 0.5
            if colab.quinzena2_alocada:
                counts_per_month[colab.quinzena2_alocada] += 0.5
            if colab.quinzena3_alocada:
                counts_per_month[colab.quinzena3_alocada] += 0.5
    
    # Refresh the list of collaborators from the database
    colaboradores_filtrados = colaborador_filter.qs
    
    # Aplicar filtros adicionais se necessário
    if request.GET.get('nome', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(nome__icontains=request.GET.get('nome'))
    if request.GET.get('re', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(re=request.GET.get('re'))
    if request.GET.get('posto', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(posto=request.GET.get('posto'))
    
    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]
    
    # Colaboradores ordenados por critérios de prioridade
    colaboradores_ordenados = ordenar_por_prioridade(colaboradores_filtrados)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="colaboradores.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nome', 'Graduacao', 'Numero RE', 'Data Ultima Promocao', 'Classificacao no Concurso', 'Data de Ingresso PM', 'Mes Alocado'])

    for colaborador in colaboradores_filtrados:
        data_ultima_promocao = colaborador.data_ultima_promocao.strftime('%d/%m/%Y') if colaborador.data_ultima_promocao else ''
        data_ingresso_pm = colaborador.data_ingresso_pm.strftime('%d/%m/%Y') if colaborador.data_ingresso_pm else ''
        classificacao_concurso = colaborador.classificacao_concurso if colaborador.classificacao_concurso else ''
        
        # Determinar o período de férias para exibição
        if colaborador.tipo_ferias == 'mensal' and colaborador.mes_alocado:
            mes_alocado = colaborador.mes_alocado
        elif colaborador.quinzena1_alocada:
            mes_alocado = f"{colaborador.quinzena1_alocada} (Quinzena)"
        else:
            mes_alocado = 'Nao alocado'
        
        writer.writerow([colaborador.nome, colaborador.graduacao, colaborador.numero_re, 
                       data_ultima_promocao, classificacao_concurso, data_ingresso_pm, mes_alocado])

    return response

def pagina_inicial(request):
    return render(request, 'gestao_colaboradores/pagina_inicial.html')

def cadastrar_colaborador(request):
    if request.method == 'POST':
        form = ColaboradorForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                return redirect('lista_colaboradores')
            except IntegrityError:
                form.add_error(None, "Erro ao cadastrar. O colaborador ja existe ou ha algum conflito de dados.")
        else:
            logging.debug(f'Form Errors: {form.errors}')  # Para depuracao: imprima erros no console
    else:
        form = ColaboradorForm()

    return render(request, 'gestao_colaboradores/cadastrar.html', {'form': form})

def lista_colaboradores(request):
    configuracao, _ = Configuracao.objects.get_or_create(id=1)
    
    if request.method == 'POST' and 'salvar_configuracao' in request.POST:
        old_limite = configuracao.limite_por_mes
        configuracao_form = ConfiguracaoForm(request.POST, instance=configuracao)
        if configuracao_form.is_valid():
            new_config = configuracao_form.save(commit=False)
            # Check if the limit has been decreased
            if new_config.limite_por_mes < old_limite:
                messages.info(request, f'Limite de alocação reduzido de {old_limite} para {new_config.limite_por_mes}. Realocando férias...')
                new_config.save()
                # Force reallocation of all vacations with the new limit
                colaboradores = alocar_ferias(Colaborador.objects.all(), new_config.limite_por_mes)
                for colaborador in colaboradores:
                    colaborador.save()
                messages.success(request, 'Férias realocadas com sucesso após redução do limite!')
                return redirect('lista_colaboradores')
            new_config.save()
            messages.success(request, 'Configuração salva com sucesso!')
            return redirect('lista_colaboradores')
    else:
        configuracao_form = ConfiguracaoForm(instance=configuracao)
    
    colaborador_filter = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all())
    colaboradores_filtrados = colaborador_filter.qs
    
    # Contar alocações por mês (somando mensais e quinzenais)
    counts_per_month = {mes: 0 for mes in MESES}
    for colab in Colaborador.objects.all():
        if colab.mes_alocado:
            counts_per_month[colab.mes_alocado] += 1
        if colab.quinzena1_alocada:
            counts_per_month[colab.quinzena1_alocada] += 0.5  # Uma quinzena conta como metade do mês
        if colab.quinzena2_alocada:
            counts_per_month[colab.quinzena2_alocada] += 0.5
        if colab.quinzena3_alocada:
            counts_per_month[colab.quinzena3_alocada] += 0.5
    
    # Verificar se há alocação
    tem_alocacao = any([
        c.mes_alocado is not None or 
        c.quinzena1_alocada is not None or 
        c.quinzena2_alocada is not None or 
        c.quinzena3_alocada is not None
        for c in Colaborador.objects.all()[:5]  # Verificar apenas alguns para desempenho
    ])
    
    # Se não houver alocação ainda, alocar as férias agora
    if not tem_alocacao:
        colaboradores = alocar_ferias(Colaborador.objects.all(), configuracao.limite_por_mes)
        # Salvar as alocações
        for colaborador in colaboradores:
            colaborador.save()
        # Recalcular counts_per_month
        counts_per_month = {mes: 0 for mes in MESES}
        for colab in Colaborador.objects.all():
            if colab.mes_alocado:
                counts_per_month[colab.mes_alocado] += 1
            if colab.quinzena1_alocada:
                counts_per_month[colab.quinzena1_alocada] += 0.5
            if colab.quinzena2_alocada:
                counts_per_month[colab.quinzena2_alocada] += 0.5
            if colab.quinzena3_alocada:
                counts_per_month[colab.quinzena3_alocada] += 0.5
    
    # Verificar quais meses atingiram o limite
    meses_limite_atingido = [mes for mes, contagem in counts_per_month.items() if contagem >= configuracao.limite_por_mes]
    
    # Refresh the list of collaborators from the database
    colaboradores_filtrados = colaborador_filter.qs
    
    # Aplicar filtros adicionais se necessário
    if request.GET.get('nome', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(nome__icontains=request.GET.get('nome'))
    if request.GET.get('re', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(re=request.GET.get('re'))
    if request.GET.get('posto', None):
        colaboradores_filtrados = colaboradores_filtrados.filter(posto=request.GET.get('posto'))
    
    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]
    
    # Colaboradores ordenados por critérios de prioridade
    colaboradores_ordenados = ordenar_por_prioridade(colaboradores_filtrados)
    
    counts_per_month_list = [(mes, counts_per_month[mes]) for mes in MESES]

    return render(request, 'gestao_colaboradores/lista.html', {
        'colaboradores': colaboradores_ordenados,
        'filter': colaborador_filter,
        'meses': MESES,
        'counts_per_month_list': counts_per_month_list,  # Renomeado para combinar com o template
        'limite_por_mes': configuracao.limite_por_mes,
        'configuracao_form': configuracao_form,
        'meses_limite_atingido': meses_limite_atingido,
    })

def extrair_preferencias_do_colaborador(colaborador):
    preferencias_mensais = []
    preferencias_quinzenais = []
    
    # Tentar extrair do nome (formato: 'JAN JUN DEZ - Soldado')
    if colaborador.nome:
        nome = colaborador.nome
        if ' - ' in nome:
            partes_nome = nome.split(' - ')[0]
        else:
            partes_nome = nome
        
        # Regex para encontrar sequências de 3 letras maiúsculas (abreviações dos meses)
        matches = re.findall(r'\b[A-Z]{3}\b', partes_nome)
        
        # Converter as abreviações em meses e criar preferências na ordem correta
        for i, match in enumerate(matches):
            if match in MES_ABREV:
                preferencias_mensais.append({
                    'mes': MES_ABREV[match],
                    'tipo': 'mensal',
                    'ordem': i + 1  # A ordem é determinada pela posição no nome
                })
    
    # Se não encontrou preferências no nome ou está vazio, usar os campos individuais
    if not preferencias_mensais:
        if colaborador.tipo_ferias == 'mensal':
            if colaborador.mes1_preferencia:
                preferencias_mensais.append({
                    'mes': colaborador.mes1_preferencia,
                    'tipo': 'mensal',
                    'ordem': 1
                })
            if colaborador.mes2_preferencia:
                preferencias_mensais.append({
                    'mes': colaborador.mes2_preferencia,
                    'tipo': 'mensal',
                    'ordem': 2
                })
            if colaborador.mes3_preferencia:
                preferencias_mensais.append({
                    'mes': colaborador.mes3_preferencia,
                    'tipo': 'mensal',
                    'ordem': 3
                })
    
    return preferencias_mensais, preferencias_quinzenais

def alocar_ferias_novo(request):
    # Obter todos os colaboradores
    colaboradores = Colaborador.objects.all()
    
    # Obter configuração do limite por mês
    configuracao = Configuracao.objects.first()
    if not configuracao:
        configuracao = Configuracao.objects.create(limite_por_mes=1)
    
    if request.method == 'POST':
        # Se estiver submetendo o formulário, realizar alocação
        colaboradores_processados = alocar_ferias(colaboradores, configuracao.limite_por_mes)
        
        # Salvar as alterações dos colaboradores
        for colaborador in colaboradores_processados:
            colaborador.save()
        
        messages.success(request, 'Férias alocadas com sucesso!')
        return redirect('lista_colaboradores')
    
    # Verificar quais meses estão com limite atingido
    contagem_por_mes = {mes: 0 for mes in MESES}
    for colaborador in colaboradores:
        if colaborador.mes_alocado:
            contagem_por_mes[colaborador.mes_alocado] += 1
    
    meses_limite_atingido = [mes for mes, contagem in contagem_por_mes.items() 
                            if contagem >= configuracao.limite_por_mes]
    
    # Criar formulário para editar configuração
    configuracao_form = None
    
    return render(request, 'gestao_colaboradores/alocar_ferias.html', {
        'colaboradores': colaboradores,
        'limite_por_mes': configuracao.limite_por_mes,
        'configuracao_form': configuracao_form,
        'meses_limite_atingido': meses_limite_atingido,
    })
