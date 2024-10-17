# gestao_colaboradores/views.py
from collections import defaultdict
from django.shortcuts import render, redirect
from .models import Colaborador
from .forms import ColaboradorForm
from .filters import ColaboradorFilter

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
