# gestao_colaboradores/views.py
from collections import defaultdict
from django.shortcuts import render, redirect
from .models import Colaborador, Configuracao
from .forms import ColaboradorForm, ConfiguracaoForm
from .filters import ColaboradorFilter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import csv
from django.db.utils import IntegrityError
from datetime import date
from django.db.models import Count


# Definir as prioridades de graduação
PRIORIDADE_GRADUACOES = {
    'Capitão': 1,
    'Tenente': 2,
    'Subtenente': 3,
    '1º Sargento': 4,
    '2º Sargento': 5,
    '3º Sargento': 6,
    'Cabo': 7,
    'Soldado': 8,
}

MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
]

def alocar_ferias(colaboradores, limite_por_mes):
    for colaborador in colaboradores:
        colaborador.mes_alocado = None
        colaborador.save()

    meses_ferias = defaultdict(list)
    colaboradores_alocados = {}
    meses_limite_atingido = set()

    for mes in MESES:
        meses_ferias[mes] = []

    colaboradores_ordenados = sorted(
        colaboradores,
        key=lambda c: (
            PRIORIDADE_GRADUACOES.get(c.graduacao, 999),
            c.data_promocao if c.data_promocao else date.min,
            c.numero_re
        )
    )

    for colaborador in colaboradores_ordenados:
        if colaborador.tipo_ferias == 'mensal':
            for mes in [colaborador.mes1_preferencia, colaborador.mes2_preferencia, colaborador.mes3_preferencia]:
                if len(meses_ferias[mes]) < limite_por_mes:
                    meses_ferias[mes].append(colaborador)
                    colaboradores_alocados[colaborador] = mes
                    colaborador.mes_alocado = mes
                    colaborador.save()
                    if len(meses_ferias[mes]) == limite_por_mes:
                        meses_limite_atingido.add(mes)
                    break
        elif colaborador.tipo_ferias == 'quinzenal':
            if colaborador.quinzena1_mes:
                mes1 = colaborador.quinzena1_mes
                if len(meses_ferias[mes1]) < limite_por_mes:
                    meses_ferias[mes1].append(colaborador)
                    colaboradores_alocados[colaborador] = mes1
                    colaborador.mes_alocado = mes1
                    colaborador.save()
                else:
                    meses_limite_atingido.add(mes1)
            if colaborador.quinzena2_mes:
                mes2 = colaborador.quinzena2_mes
                if len(meses_ferias[mes2]) < limite_por_mes:
                    if mes1 == mes2 and colaboradores_alocados.get(colaborador) == mes1:
                        continue
                    meses_ferias[mes2].append(colaborador)
                    colaboradores_alocados[colaborador] = mes2
                    colaborador.mes_alocado = mes2
                    colaborador.save()
                else:
                    meses_limite_atingido.add(mes2)

    return colaboradores_alocados, meses_limite_atingido

# Função para listar os colaboradores com filtro e ordenação
def lista_colaboradores(request):
    configuracao, _ = Configuracao.objects.get_or_create(id=1)
    
    if request.method == 'POST' and 'salvar_configuracao' in request.POST:
        configuracao_form = ConfiguracaoForm(request.POST, instance=configuracao)
        if configuracao_form.is_valid():
            configuracao_form.save()
            return redirect('lista_colaboradores')
    else:
        configuracao_form = ConfiguracaoForm(instance=configuracao)
    
    colaborador_filter = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all())
    colaboradores_filtrados = colaborador_filter.qs

    ferias_alocadas, meses_limite_atingido = alocar_ferias(colaboradores_filtrados, configuracao.limite_por_mes)

    for colaborador in colaboradores_filtrados:
        colaborador.mes_alocado = ferias_alocadas.get(colaborador)

    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]
    
    colaboradores_ordenados = sorted(
        colaboradores_filtrados,
        key=lambda c: (
            PRIORIDADE_GRADUACOES.get(c.graduacao, 999),
            c.data_promocao if c.data_promocao else date.min,
            c.numero_re
        )
    )
    
    counts_per_month_qs = Colaborador.objects.exclude(mes_alocado__isnull=True).values('mes_alocado').annotate(total=Count('mes_alocado'))
    counts_per_month = {mes: 0 for mes in MESES}
    for item in counts_per_month_qs:
        mes = item['mes_alocado']
        total = item['total']
        counts_per_month[mes] = total
    counts_per_month_list = [(mes, counts_per_month[mes]) for mes in MESES]

    return render(request, 'gestao_colaboradores/lista.html', {
        'colaboradores': colaboradores_ordenados,
        'filter': colaborador_filter,
        'MESES': MESES,
        'meses_limite_atingido': meses_limite_atingido,
        'counts_per_month_list': counts_per_month_list,
        'configuracao_form': configuracao_form,
        'configuracao': configuracao,
    })


import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)

def cadastrar_colaborador(request):
    if request.method == 'POST':
        form = ColaboradorForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                return redirect('lista_colaboradores')
            except IntegrityError:
                form.add_error(None, "Erro ao cadastrar. O colaborador já existe ou há algum conflito de dados.")
        else:
            logging.debug(f'Form Errors: {form.errors}')  # Para depuração: imprima erros no console
    else:
        form = ColaboradorForm()

    return render(request, 'gestao_colaboradores/cadastrar.html', {'form': form})


def exportar_pdf(request):
    colaboradores_filtrados = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all()).qs
    ferias_alocadas, meses_limite_atingido = alocar_ferias(colaboradores_filtrados, 13)  # Adicionando limite padrão

    for colaborador in colaboradores_filtrados:
        colaborador.mes_alocado = ferias_alocadas.get(colaborador)

    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]

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
        p.drawString(50, y, f"Graduação: {colaborador.graduacao}")
        y -= 20
        p.drawString(50, y, f"Número de RE: {colaborador.numero_re}")
        y -= 20
        data_promocao = colaborador.data_promocao.strftime('%d/%m/%Y') if colaborador.data_promocao else 'Não informada'
        p.drawString(50, y, f"Data da Última Promoção: {data_promocao}")
        y -= 20
        mes_alocado = colaborador.mes_alocado if colaborador.mes_alocado else 'Não alocado'
        p.drawString(50, y, f"Mês Alocado: {mes_alocado}")
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
    configuracao, _ = Configuracao.objects.get_or_create(id=1)

    ferias_alocadas, meses_limite_atingido = alocar_ferias(colaboradores_filtrados, configuracao.limite_por_mes)

    for colaborador in colaboradores_filtrados:
        colaborador.mes_alocado = ferias_alocadas.get(colaborador)

    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="colaboradores.csv"'

    writer = csv.writer(response, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Nome', 'Graduação', 'Número de RE', 'Data da Última Promoção', 'Mês Alocado'])

    def remover_caracteres_especiais(texto):
        return ''.join(e for e in texto if e.isalnum() or e.isspace() or e == '-')

    for colaborador in colaboradores_filtrados:
        nome = remover_caracteres_especiais(colaborador.nome)
        graduacao = remover_caracteres_especiais(colaborador.graduacao)
        numero_re = remover_caracteres_especiais(str(colaborador.numero_re))
        data_promocao = colaborador.data_promocao.strftime('%d/%m/%Y') if colaborador.data_promocao else ''
        mes_alocado = colaborador.mes_alocado if colaborador.mes_alocado else 'Não alocado'
        
        writer.writerow([nome, graduacao, numero_re, data_promocao, mes_alocado])

    return response


def pagina_inicial(request):
    return render(request, 'gestao_colaboradores/pagina_inicial.html')
