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
    # Resetar o mês alocado para todos os colaboradores filtrados
    for colaborador in colaboradores:
        colaborador.mes_alocado = None
        colaborador.save()

    meses_ferias = defaultdict(list)
    colaboradores_alocados = {}
    meses_limite_atingido = set()

    # Inicializar os meses no dicionário
    for mes in MESES:
        meses_ferias[mes] = []

    # Ordenar colaboradores de acordo com as regras de prioridade
    colaboradores_ordenados = sorted(
        colaboradores,
        key=lambda c: (
            PRIORIDADE_GRADUACOES.get(c.graduacao, 999),
            c.data_promocao if c.data_promocao else date.min,
            c.numero_re
        )
    )

    # Alocar colaboradores nos meses de preferência
    for colaborador in colaboradores_ordenados:
        alocado = False
        for mes in [colaborador.mes1_preferencia, colaborador.mes2_preferencia, colaborador.mes3_preferencia]:
            if len(meses_ferias[mes]) < limite_por_mes:
                meses_ferias[mes].append(colaborador)
                colaboradores_alocados[colaborador] = mes
                colaborador.mes_alocado = mes
                colaborador.save()
                alocado = True
                if len(meses_ferias[mes]) == limite_por_mes:
                    meses_limite_atingido.add(mes)
                break

        if not alocado:
            meses_disponiveis = [mes for mes in MESES if len(meses_ferias[mes]) < limite_por_mes]
            if meses_disponiveis:
                mes_menos_lotado = min(meses_disponiveis, key=lambda mes: len(meses_ferias[mes]))
                meses_ferias[mes_menos_lotado].append(colaborador)
                colaboradores_alocados[colaborador] = mes_menos_lotado
                colaborador.mes_alocado = mes_menos_lotado
                colaborador.save()
                if len(meses_ferias[mes_menos_lotado]) == limite_por_mes:
                    meses_limite_atingido.add(mes_menos_lotado)
            else:
                colaboradores_alocados[colaborador] = None

    return colaboradores_alocados, meses_limite_atingido

# Função para listar os colaboradores com filtro e ordenação
def lista_colaboradores(request):
    # Carregar ou criar a configuração
    configuracao, _ = Configuracao.objects.get_or_create(id=1)
    
    # Processar o formulário de configuração
    if request.method == 'POST' and 'salvar_configuracao' in request.POST:
        configuracao_form = ConfiguracaoForm(request.POST, instance=configuracao)
        if configuracao_form.is_valid():
            configuracao_form.save()
            return redirect('lista_colaboradores')  # Redireciona para recalcular as alocações
    else:
        configuracao_form = ConfiguracaoForm(instance=configuracao)
    
    # Criar o filtro de colaboradores
    colaborador_filter = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all())
    colaboradores_filtrados = colaborador_filter.qs

    # Alocar as férias usando o limite definido
    ferias_alocadas, meses_limite_atingido = alocar_ferias(colaboradores_filtrados, configuracao.limite_por_mes)

    # Associar o mês alocado a cada colaborador filtrado
    for colaborador in colaboradores_filtrados:
        colaborador.mes_alocado = ferias_alocadas.get(colaborador)
    
    # Aplicar o filtro ao mês efetivamente alocado
    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]
    
    # Ordenar os colaboradores filtrados de acordo com as regras de prioridade
    colaboradores_ordenados = sorted(
        colaboradores_filtrados,
        key=lambda c: (
            PRIORIDADE_GRADUACOES.get(c.graduacao, 999),
            c.data_promocao if c.data_promocao else date.min,
            c.numero_re
        )
    )
    
    # Calcular a quantidade de colaboradores alocados em cada mês
    counts_per_month_qs = Colaborador.objects.exclude(mes_alocado__isnull=True).values('mes_alocado').annotate(total=Count('mes_alocado'))
    counts_per_month = {mes: 0 for mes in MESES}
    for item in counts_per_month_qs:
        mes = item['mes_alocado']
        total = item['total']
        counts_per_month[mes] = total
    counts_per_month_list = [(mes, counts_per_month[mes]) for mes in MESES]
    
    # Renderizar o template
    return render(request, 'gestao_colaboradores/lista.html', {
        'colaboradores': colaboradores_ordenados,
        'filter': colaborador_filter,
        'MESES': MESES,
        'meses_limite_atingido': meses_limite_atingido,
        'counts_per_month_list': counts_per_month_list,
        'configuracao_form': configuracao_form,  # Passando o formulário para o template
        'configuracao': configuracao,
    })


def cadastrar_colaborador(request):
    if request.method == 'POST':
        form = ColaboradorForm(request.POST)
        if form.is_valid():
            try:
                form.save()  # Salva o colaborador no banco de dados
                return redirect('lista_colaboradores')  # Redireciona para a lista após o cadastro
            except IntegrityError:
                form.add_error(None, "Erro ao cadastrar. O colaborador já existe ou há algum conflito de dados.")
    else:
        form = ColaboradorForm()

    return render(request, 'gestao_colaboradores/cadastrar.html', {'form': form})

def pagina_inicial(request):
    return render(request, 'gestao_colaboradores/pagina_inicial.html')

# Função para gerar PDF
def exportar_pdf(request):
    # Obtenha os colaboradores filtrados
    colaboradores_filtrados = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all()).qs

    # Alocar as férias para cada colaborador filtrado
    ferias_alocadas, meses_limite_atingido = alocar_ferias(colaboradores_filtrados)

    # Associar o mês alocado
    for colaborador in colaboradores_filtrados:
        colaborador.mes_alocado = ferias_alocadas.get(colaborador)

    # Aplicar o filtro ao mês efetivamente alocado
    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]

    # Configurar o response para PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="colaboradores.pdf"'

    # Criar o PDF
    p = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    # Definir um título
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, altura - 50, "Lista dos Efetivos")

    # Adicionar colaboradores filtrados ao PDF
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
        y -= 30  # Espaço extra entre colaboradores

        # Verificar se precisa criar uma nova página
        if y < 50:
            p.showPage()
            y = altura - 50
            p.setFont("Helvetica", 12)

    p.save()
    return response

# Função para exportar CSV
def exportar_csv(request):
    # Obtenha os colaboradores filtrados
    colaborador_filter = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all())
    colaboradores_filtrados = colaborador_filter.qs

    # Carregar a configuração atual
    configuracao, _ = Configuracao.objects.get_or_create(id=1)

    # Alocar as férias usando o limite definido
    ferias_alocadas, meses_limite_atingido = alocar_ferias(colaboradores_filtrados, configuracao.limite_por_mes)

    # Associar o mês alocado
    for colaborador in colaboradores_filtrados:
        colaborador.mes_alocado = ferias_alocadas.get(colaborador)

    # Aplicar o filtro ao mês efetivamente alocado
    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]

    # Configurar o response para CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="colaboradores.csv"'

    writer = csv.writer(response, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Nome', 'Graduação', 'Número de RE', 'Data da Última Promoção', 'Mês Alocado'])

    # Função para remover caracteres especiais
    def remover_caracteres_especiais(texto):
        return ''.join(e for e in texto if e.isalnum() or e.isspace() or e == '-')

    # Escreva os dados dos colaboradores filtrados
    for colaborador in colaboradores_filtrados:
        nome = remover_caracteres_especiais(colaborador.nome)
        graduacao = remover_caracteres_especiais(colaborador.graduacao)
        numero_re = remover_caracteres_especiais(str(colaborador.numero_re))
        data_promocao = colaborador.data_promocao.strftime('%d/%m/%Y') if colaborador.data_promocao else ''
        mes_alocado = colaborador.mes_alocado if colaborador.mes_alocado else 'Não alocado'
        
        writer.writerow([nome, graduacao, numero_re, data_promocao, mes_alocado])

    return response