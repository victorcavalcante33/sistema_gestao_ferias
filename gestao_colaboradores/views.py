# gestao_colaboradores/views.py
from collections import defaultdict
from django.shortcuts import render, redirect
from .models import Colaborador
from .forms import ColaboradorForm
from .filters import ColaboradorFilter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import csv

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

# Função para alocar as férias de acordo com as preferências
def alocar_ferias(colaboradores):
    limite_por_mes = int(Colaborador.objects.count() * 0.20)
    meses_ferias = defaultdict(list)
    colaboradores_alocados = {}

    # Ordenar colaboradores de acordo com as regras de prioridade
    colaboradores_ordenados = sorted(
        colaboradores,
        key=lambda c: (
            PRIORIDADE_GRADUACOES[c.graduacao],
            c.numero_re if c.graduacao == 'Soldado' else c.data_promocao
        )
    )

    # Alocar colaboradores nos meses de preferência
    for colaborador in colaboradores_ordenados:
        alocado = False
        for mes in [colaborador.mes1_preferencia, colaborador.mes2_preferencia, colaborador.mes3_preferencia]:
            if len(meses_ferias[mes]) < limite_por_mes:
                meses_ferias[mes].append(colaborador.nome)
                colaboradores_alocados[colaborador.nome] = mes  # Armazena o mês alocado
                alocado = True
                break
        
        # Se não foi possível alocar nas preferências, alocar no mês com menos pessoas
        if not alocado:
            mes_menos_lotado = min(meses_ferias, key=lambda k: len(meses_ferias[k]))
            meses_ferias[mes_menos_lotado].append(colaborador.nome)
            colaboradores_alocados[colaborador.nome] = mes_menos_lotado  # Armazena o mês alocado

    return colaboradores_alocados

# Função para listar os colaboradores com filtro e ordenação
def lista_colaboradores(request):
    # Criar o filtro de graduação, número de RE, e data de promoção
    colaborador_filter = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all())
    
    # Aplicar o filtro primeiro
    colaboradores_filtrados = colaborador_filter.qs

    # Alocar as férias para cada colaborador filtrado
    ferias_alocadas = alocar_ferias(colaboradores_filtrados)

    # Associar o mês alocado a cada colaborador filtrado
    for colaborador in colaboradores_filtrados:
        colaborador.mes_alocado = ferias_alocadas.get(colaborador.nome)

    # Aplicar o filtro ao mês efetivamente alocado
    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if colab.mes_alocado == mes_filtrado]

    # Ordenar os colaboradores filtrados de acordo com as regras de prioridade
    colaboradores_ordenados = sorted(
        colaboradores_filtrados,
        key=lambda c: (
            PRIORIDADE_GRADUACOES[c.graduacao],  # Ordena pela graduação
            c.numero_re if c.graduacao == 'Soldado' else c.data_promocao  # Ordena por número de RE para soldados, data de promoção para os demais
        )
    )

    # Renderizar o template com os colaboradores filtrados e ordenados
    return render(request, 'gestao_colaboradores/lista.html', {'colaboradores': colaboradores_ordenados, 'filter': colaborador_filter})


def cadastrar_colaborador(request):
    if request.method == 'POST':
        form = ColaboradorForm(request.POST)
        if form.is_valid():
            form.save()  # Salva o colaborador no banco de dados
            return redirect('lista_colaboradores')  # Redireciona para a lista de colaboradores após o cadastro
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
    ferias_alocadas = alocar_ferias(colaboradores_filtrados)

    # Aplicar o filtro ao mês efetivamente alocado
    mes_filtrado = request.GET.get('mes_alocado', None)
    if mes_filtrado:
        colaboradores_filtrados = [colab for colab in colaboradores_filtrados if ferias_alocadas.get(colab.nome) == mes_filtrado]

    # Configurar o response para PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="colaboradores.pdf"'

    # Criar o PDF
    p = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    # Definir um título
    p.drawString(100, altura - 100, "Lista de Colaboradores Filtrados")

    # Adicionar colaboradores filtrados ao PDF
    y = altura - 120
    for colaborador in colaboradores_filtrados:
        p.drawString(100, y, f"Nome: {colaborador.nome}")
        y -= 20
        p.drawString(100, y, f"Graduação: {colaborador.graduacao}")
        y -= 20
        p.drawString(100, y, f"Número de RE: {colaborador.numero_re}")
        y -= 20
        p.drawString(100, y, f"Data da Última Promoção: {colaborador.data_promocao}")
        y -= 20
        p.drawString(100, y, f"Mês Alocado: {ferias_alocadas.get(colaborador.nome, 'Não alocado')}")
        y -= 30  # Espaço extra entre colaboradores

    p.showPage()
    p.save()
    return response

# Função para exportar CSV
def exportar_csv(request):
    # Obtenha os colaboradores filtrados
    colaboradores_filtrados = ColaboradorFilter(request.GET, queryset=Colaborador.objects.all()).qs

    # Configurar o response para CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="colaboradores.csv"'

    writer = csv.writer(response, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Nome', 'Graduacao', 'Numero de RE', 'Data da Ultima Promocao'])

    # Função para remover caracteres especiais
    def remover_caracteres_especiais(texto):
        return ''.join(e for e in texto if e.isalnum() or e.isspace() or e == '-')

    # Escreva os dados dos colaboradores filtrados
    for colaborador in colaboradores_filtrados:
        nome = remover_caracteres_especiais(colaborador.nome)
        graduacao = remover_caracteres_especiais(colaborador.graduacao)
        numero_re = remover_caracteres_especiais(str(colaborador.numero_re))
        data_promocao = colaborador.data_promocao.strftime('%d/%m/%Y') if colaborador.data_promocao else ''
        
        writer.writerow([nome, graduacao, numero_re, data_promocao])

    return response


