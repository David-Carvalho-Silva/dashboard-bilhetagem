import dash
from dash import dcc, html, Input, Output, dash_table,State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from db_bilhetagem import get_engine
import datetime
from sqlalchemy import text
import plotly.graph_objects as go
import locale

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')

# 1) Conexão e carregamento de dados
engine = get_engine()

def remove_pedidos_ja_pagos(engine):
    """
    Remove da tabela pedidos_provider_v2 todos os pedidos em status 'Novo'
    cujo 'Nº Pedido' também existe na tabela boletos_pago_v3 (ou seja, já foram pagos).
    """
    with engine.begin() as conn:
        delete_query = text("""
            DELETE FROM `db_bilhetagem`.`pedidos_provider_v2`
            WHERE `Status` = 'Novo'
            AND `Nº Pedido` IN (
                SELECT DISTINCT `Número Pedido`
                FROM `db_bilhetagem`.`boletos_pago_v3`
            );
        """)
        conn.execute(delete_query)

def load_pedidos_data():
    """Carrega os dados da tabela pedidos_provider_v2, removendo antes os pedidos já pagos."""
    remove_pedidos_ja_pagos(engine)
    query = "SELECT * FROM pedidos_provider_v2"
    df = pd.read_sql(query, engine)
    return df

df_pedidos = load_pedidos_data()

# 2) Conversão da coluna de data para datetime
df_pedidos['Data do Pedido'] = pd.to_datetime(
    df_pedidos['Data do Pedido'], format='%d/%m/%Y', errors='coerce'
)

# 3) Cópia do DataFrame para manipulação
df_novo = df_pedidos.copy()

# Define as datas mínimas e máximas para o seletor de data
if not df_novo.empty:
    min_date = df_novo['Data do Pedido'].min().date()
    max_date = df_novo['Data do Pedido'].max().date()
else:
    hoje = pd.to_datetime('today').date()
    min_date = hoje
    max_date = hoje

hoje = pd.Timestamp.now().normalize().date()
tres_meses_atras = (hoje - pd.DateOffset(months=2)).replace(day=1).date()
start_date_default = max(tres_meses_atras, min_date)
end_date_default   = min(hoje, max_date)

def filtrar_pedidos_vencidos(df):
    """
    Retorna apenas os pedidos que:
      - Estão em status 'Novo'
      - Estão vencidos (Data do Pedido entre 5 e 29 dias atrás)
    """
    df_aberto = df[df['Status'] == 'Novo'].copy()
    hoje_normalizado = pd.Timestamp.now().normalize()
    df_aberto['DiasDesdePedido'] = (hoje_normalizado - df_aberto['Data do Pedido']).dt.days
    df_vencidos = df_aberto[(df_aberto['DiasDesdePedido'] >= 5) & (df_aberto['DiasDesdePedido'] < 30)].copy()
    return df_vencidos

# 4) Inicializa o aplicativo Dash com tema escuro do Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

app.layout = html.Div(
    style={
        "backgroundColor": "#1f1f3d",
        "minHeight": "100vh",
        "padding": "20px"
    },
    children=[
        html.H1(
            "Dashboard - Pedidos com Status Novo",
            style={
                'textAlign': 'center',
                'color': '#ffffff',
                'marginBottom': '30px'
            }
        ),
        # Card com seletor de data
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px",},
            children=[
                html.Label("Selecione o período:", style={"color": "#ffffff"}),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    min_date_allowed=min_date,
                    max_date_allowed=max_date,
                    start_date=start_date_default,
                    end_date=end_date_default,
                    display_format='YYYY-MM-DD',
                    style={"backgroundColor": "#2a2b4f"}
                )
            ]
        ),
        # GRÁFICO 1: Taxa de Conversão de Pedidos em Pagamentos
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[ dcc.Graph(id='graph-novo') ]
        ),


        # GRÁFICO : Quantidade de Vales Pagos por Mês
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[ dcc.Graph(id='graph-vales') ]
        ),


        
        # GRÁFICO 2: Pedidos vencidos agrupados por faixa (5 a 29 dias)
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[ dcc.Graph(id='graph-vencimento') ]
        ),
        # Tabela para detalhes ao clicar no gráfico de vencidos
        # No layout principal, onde está o Card da tabela de pedidos vencidos, substitua por:
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[
                html.H4("Detalhes dos Pedidos Vencidos (Clique em uma barra acima)", style={"color": "#ffffff"}),
                dash_table.DataTable(
                    id='table-vencidos',
                    columns=[{"name": col, "id": col} for col in df_pedidos.columns],
                    data=[],
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_header={'backgroundColor': '#2a2b4f', 'color': 'white'},
                    style_cell={'backgroundColor': '#1f1f3d', 'color': 'white'}
                ),
                html.Br(),
                html.Button(
                    "Exportar para Excel",
                    id="btn-export-excel",
                    n_clicks=0,
                    style={
                        "width": "190px",            # Ajusta a largura
                        "height": "40px",          # Ajusta a altura
                        "backgroundColor": "#48C9B0",  # Tom de verde (ajuste conforme desejar)
                        "color": "#FFFFFF",           # Cor branca para o texto
                        "fontWeight": "300",          # Fonte mais “leve” (pode usar 400 ou 600, se preferir)
                        "border": "none",             # Remove a borda padrão
                        "borderRadius": "4px",        # Borda levemente arredondada
                        "padding": "8px 16px",        # Espaçamento interno
                        "cursor": "pointer"           # Cursor tipo “mãozinha” ao passar sobre o botão
                    }
                ),

                dcc.Download(id="download-table-vencidos")
            ]
        ),

        # GRÁFICO 3: Previsão vs. Realizado Mensal
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[ dcc.Graph(id='graph-previsao') ]
        ),
        # GRÁFICO 4: Tempo Médio entre Emissão e Pagamento
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[dcc.Graph(id='graph-tempo-medio')]
        ),

        #Quantidade de Empresas que Pagaram
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[ dcc.Graph(id='graph-pago-empresas') ]
        ),

        # GRÁFICO : Ticket Médio por Mês
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[ dcc.Graph(id='graph-ticket-medio') ]
        ),


        # GRÁFICO 5: Ranking das Empresas com Mais Atrasos de Pagamento
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[ dcc.Graph(id='graph-empresas') ]
        ),
        # GRÁFICO 6: Top 10 Empresas com Maiores Valores Devidos (Atraso > 5 dias)
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[dcc.Graph(id='graph-evolucao')]
        ),
                # Novo DataTable para detalhes dos boletos em atraso (Empresa selecionada no Gráfico 6)
        dbc.Card(
            style={"backgroundColor": "#2a2b4f", "padding": "20px", "marginBottom": "30px"},
            children=[
                html.H4("Detalhes dos Boletos em Atraso", style={"color": "#ffffff"}),
                dash_table.DataTable(
                    id='table-devedores',
                    columns=[{"name": col, "id": col} for col in df_pedidos.columns],
                    data=[],
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_header={'backgroundColor': '#2a2b4f', 'color': 'white'},
                    style_cell={'backgroundColor': '#1f1f3d', 'color': 'white'}
                )
            ]
        ),

    ]
)

# ----------------------------------------------------------------------------
# CALLBACK 1: Atualiza os gráficos
# ----------------------------------------------------------------------------
@app.callback(
    [
        Output('graph-novo', 'figure'),
        Output('graph-pago-empresas', 'figure'),
        Output('graph-vencimento', 'figure'),
        Output('graph-previsao', 'figure'),
        Output('graph-tempo-medio', 'figure'),
        Output('graph-empresas', 'figure'),
        Output('graph-evolucao', 'figure'),
        Output('graph-vales', 'figure'),
        Output('graph-ticket-medio', 'figure')  # Novo gráfico de Ticket Médio
    ],
    [
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date')
    ]
)



def update_graphs(start_date, end_date):
    # Filtra os dados conforme o intervalo selecionado
    if start_date and end_date:
        mask = (df_novo['Data do Pedido'] >= start_date) & (df_novo['Data do Pedido'] <= end_date)
        filtered_df = df_novo.loc[mask].copy()
    else:
        filtered_df = df_novo.copy()

    ############# GRÁFICO : Taxa de conversão de pedidos em pagamentos (Barras mensais)

    filtered_df['YearMonth'] = filtered_df['Data do Pedido'].dt.to_period('M')
    df_emitidos = filtered_df.groupby('YearMonth').size().reset_index(name='TotalEmitidos')
    df_pagos = filtered_df[filtered_df['Status'].isin(['Pago', 'Pago e Liberado'])]\
        .groupby('YearMonth').size().reset_index(name='TotalPagos')
    df_taxa = pd.merge(df_emitidos, df_pagos, on='YearMonth', how='left').fillna(0)
    df_taxa['TaxaConversao'] = (df_taxa['TotalPagos'] / df_taxa['TotalEmitidos']) * 100
    df_taxa.sort_values('YearMonth', inplace=True)
    df_taxa['MesAno'] = df_taxa['YearMonth'].dt.strftime('%b/%Y')
    fig_conversao = px.bar(
        df_taxa,
        x='MesAno',
        y='TaxaConversao',
        text='TaxaConversao',
        title='Taxa de Conversão Mensal (%)',
        labels={'MesAno':'Mês/Ano', 'TaxaConversao':'Taxa de Conversão (%)'}
    )
    fig_conversao.update_layout(
        title_font_size=24,
        template='plotly_dark',
        paper_bgcolor='#2a2b4f',
        plot_bgcolor='#2a2b4f',
        font_color='white',
        margin=dict(l=20, r=20, t=50, b=20),
        bargap=0.4,
        hoverlabel=dict(bgcolor='#48C9B0', font_size=14, font_family='Arial')
    )
    fig_conversao.update_traces(
        marker_color='#38b6ff',
        texttemplate='%{text:.2f}%',
        textposition='outside',
        hovertemplate='Mês: %{x}<br>Taxa de Conversão: %{y:.2f}%<extra></extra>'
    )
    min_val = df_taxa['TaxaConversao'].min()
    max_val = df_taxa['TaxaConversao'].max()
    margin = 10
    yaxis_min = max(0, min_val - margin)
    yaxis_max = min(100, max_val + margin)
    fig_conversao.update_yaxes(range=[yaxis_min, yaxis_max])



    ##############  GRÁFICO: Quantidade de Vales Pagos por Mês

    query_vales = "SELECT Pagamento, Valor FROM boletos_pago_v3"
    df_vales = pd.read_sql(query_vales, engine)
    
    df_vales['Pagamento'] = pd.to_datetime(df_vales['Pagamento'], format='%d/%m/%Y', errors='coerce')
    df_vales.dropna(subset=['Pagamento', 'Valor'], inplace=True)
    df_vales['Valor'] = (
        df_vales['Valor']
        .str.replace('R$', '', regex=False)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df_vales['Valor'] = pd.to_numeric(df_vales['Valor'], errors='coerce')
    
    if start_date and end_date:
        start_date_dt = pd.to_datetime(start_date)
        end_date_dt = pd.to_datetime(end_date)
        df_vales = df_vales[(df_vales['Pagamento'] >= start_date_dt) & (df_vales['Pagamento'] <= end_date_dt)]
    
    df_vales['MesAno'] = df_vales['Pagamento'].dt.to_period('M')
    df_vales_group = df_vales.groupby('MesAno')['Valor'].sum().reset_index(name='ValorPago')
    df_vales_group.sort_values('MesAno', inplace=True)
    df_vales_group['MesAnoLabel'] = df_vales_group['MesAno'].dt.strftime('%b/%Y')
    
    # Calcula a quantidade de vales pagos dividindo o valor total por 4,5
    df_vales_group['QtdVales'] = df_vales_group['ValorPago'] / 4.5
    # Cria uma coluna com a formatação desejada: separador de milhares como ponto e sem casas decimais
    df_vales_group['QtdValesFormat'] = df_vales_group['QtdVales'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
    
    fig_vales = px.bar(
        df_vales_group,
        x='MesAnoLabel',
        y='QtdVales',
        title='Quantidade de Vales Pagos por Mês',
        labels={'MesAnoLabel': 'Mês/Ano', 'QtdVales': 'Quantidade de Vales'},
        custom_data=['QtdValesFormat'] ,
        text='QtdValesFormat' 
    )
    fig_vales.update_layout(
        title_font_size=24,
        template="plotly_dark",
        paper_bgcolor="#2a2b4f",
        plot_bgcolor="#2a2b4f",
        font_color="white",
        xaxis=dict(type='category'),
        bargap=0.4,
        separators=".," ,
        hoverlabel=dict(bgcolor='#48C9B0', font_size=14, font_family='Arial') 
    )
    fig_vales.update_traces(
    marker_color='#38b6ff',
    textposition='outside',  # Posiciona os rótulos fora das barras
    texttemplate='%{text}',   # Exibe o valor exatamente como está na coluna QtdValesFormat
    hovertemplate='Quantidade de Vales: %{customdata[0]}<extra></extra>'
    )

  


    ################ GRÁFICO : Pedidos vencidos agrupados por faixa (5 a 29 dias)
    df_vencidos = filtrar_pedidos_vencidos(filtered_df)
    def categorize_vencimento(x):
        if x == 5:
            return "5 dias"
        elif 6 <= x <= 10:
            return "6 a 10 dias"
        elif 11 <= x < 30:
            return "11 a 29 dias"
        else:
            return None
    if not df_vencidos.empty:
        df_vencidos['FaixaVencimento'] = df_vencidos['DiasDesdePedido'].apply(categorize_vencimento)
        grouped_venc = df_vencidos.groupby('FaixaVencimento').size().reset_index(name='Quantidade')
        grouped_venc['FaixaVencimento'] = pd.Categorical(
            grouped_venc['FaixaVencimento'],
            categories=["5 dias", "6 a 10 dias", "11 a 29 dias"],
            ordered=True
        )
    else:
        grouped_venc = pd.DataFrame({'FaixaVencimento': [], 'Quantidade': []})
    fig_vencimento = px.bar(
        grouped_venc,
        x='FaixaVencimento',
        y='Quantidade',
        title='Pedidos Vencidos (5 a 29 dias) Agrupados em Faixas',
        category_orders={"FaixaVencimento": ["5 dias", "6 a 10 dias", "11 a 29 dias"]}
    )
    fig_vencimento.update_layout(
        template="plotly_dark",
        paper_bgcolor="#2a2b4f",
        plot_bgcolor="#2a2b4f",
        font_color="white",
        xaxis_title="Faixa de Atraso",
        yaxis_title="Quantidade de Pedidos",
        hoverlabel=dict(bgcolor='#f39c12', font_size=14, font_family='Arial')
    )
    fig_vencimento.update_traces(marker_color="#38b6ff")



    # GRÁFICO : Previsão vs. Pagamento Acumulado (Reset Mensal)


    df_previsao = df_novo[df_novo['Status'].isin(['Novo', 'Pago e Liberado'])].copy()
    df_previsto = pd.DataFrame()
    if not df_previsao.empty and 'Valor Crédito' in df_previsao.columns:
        df_previsao['Valor Crédito'] = (
            df_previsao['Valor Crédito']
            .str.replace('R$', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
        )
        df_previsao['Valor Crédito'] = pd.to_numeric(df_previsao['Valor Crédito'], errors='coerce')
        df_previsao['Data do Pedido'] = pd.to_datetime(df_previsao['Data do Pedido'], dayfirst=True, errors='coerce')
        df_previsao['PrevisaoRecebimento'] = df_previsao['Data do Pedido'] + pd.DateOffset(days=5)
        
        df_previsto = (
            df_previsao
            .groupby(df_previsao['PrevisaoRecebimento'].dt.date)['Valor Crédito']
            .sum()
            .reset_index()
        )
        df_previsto.columns = ['Data', 'ValorPrevisto']
    if not df_previsto.empty:
        df_previsto['Data'] = pd.to_datetime(df_previsto['Data'])
        df_previsto['year_month'] = df_previsto['Data'].dt.to_period('M')
        df_previsto['ValorPrevistoAcumulado'] = df_previsto.groupby('year_month')['ValorPrevisto'].cumsum()
        today_ts = pd.Timestamp.today()
        current_month_start = today_ts.replace(day=1)
        previous_month_start = current_month_start - pd.DateOffset(months=2)
        next_month_start = current_month_start + pd.DateOffset(months=1)
        df_previsto_filtered = df_previsto[
            (df_previsto['Data'] >= previous_month_start) &
            (df_previsto['Data'] < next_month_start)
        ].copy()
        df_previsto_filtered.sort_values('Data', inplace=True)
    else:
        df_previsto_filtered = pd.DataFrame(columns=['Data', 'ValorPrevistoAcumulado'])
    
    
    
    df_pago = df_novo[df_novo['Status'] == 'Pago e Liberado'].copy()
    df_pago['Valor Crédito'] = (
        df_pago['Valor Crédito']
        .str.replace('R$', '', regex=False)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df_pago['Valor Crédito'] = pd.to_numeric(df_pago['Valor Crédito'], errors='coerce')
    if not df_pago.empty and 'Nº Pedido' in df_pago.columns:
        query_boletos = "SELECT * FROM boletos_pago_v3"
        df_boletos = pd.read_sql(query_boletos, engine)
        df_boletos['Pagamento'] = pd.to_datetime(df_boletos['Pagamento'], format='%d/%m/%Y', errors='coerce')
        df_boletos['Valor'] = (
            df_boletos['Valor']
            .str.replace('R$', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
        )
        df_boletos['Valor'] = pd.to_numeric(df_boletos['Valor'], errors='coerce')
        df_pago['Nº Pedido'] = df_pago['Nº Pedido'].astype(str).str.strip()
        df_boletos['Número Pedido'] = df_boletos['Número Pedido'].astype(str).str.strip()
        df_pago_merged = pd.merge(
            df_pago,
            df_boletos,
            left_on='Nº Pedido',
            right_on='Número Pedido',
            how='left'
        )
        df_pago_merged = df_pago_merged[
            df_pago_merged['Número Pedido'].notna() & (df_pago_merged['Número Pedido'] != "")
        ]
        
        df_pago_merged['ValorFinal'] = df_pago_merged['Valor'].combine_first(df_pago_merged['Valor Crédito'])
        df_pago_merged['DataPagamento'] = df_pago_merged['Pagamento'].combine_first(df_pago_merged['Data do Pedido'])
       
        df_pago_grouped = (
            df_pago_merged
            .groupby(df_pago_merged['DataPagamento'].dt.date)['ValorFinal']
            .sum()
            .reset_index()
        )
        df_pago_grouped.columns = ['Data', 'ValorPago']
        if not df_pago_grouped.empty:
            df_pago_grouped['Data'] = pd.to_datetime(df_pago_grouped['Data'])
            df_pago_grouped['year_month'] = df_pago_grouped['Data'].dt.to_period('M')
            df_pago_grouped['ValorPagoAcumulado'] = df_pago_grouped.groupby('year_month')['ValorPago'].cumsum()
            df_pago_filtered = df_pago_grouped[
                (df_pago_grouped['Data'] >= previous_month_start) &
                (df_pago_grouped['Data'] < next_month_start)
            ].copy()
            df_pago_filtered.sort_values('Data', inplace=True)
        else:
            df_pago_filtered = pd.DataFrame(columns=['Data', 'ValorPagoAcumulado'])
    else:
        df_pago_filtered = pd.DataFrame(columns=['Data', 'ValorPagoAcumulado'])
    print(df_pago_filtered)
  
    fig_previsao = go.Figure()
    if not df_previsto_filtered.empty:
        fig_previsao.add_trace(go.Scatter(
            x=df_previsto_filtered['Data'],
            y=df_previsto_filtered['ValorPrevistoAcumulado'],
            mode='lines+markers',
            name='Previsto Acumulado',
            line=dict(color='#3498db', width=3),
            marker=dict(size=8),
            hovertemplate="Data: %{x|%d/%m/%Y}<br>Valor Previsto: %{y:,.2f}<extra></extra>"

        ))
    if not df_pago_filtered.empty:
        fig_previsao.add_trace(go.Scatter(
            x=df_pago_filtered['Data'],
            y=df_pago_filtered['ValorPagoAcumulado'],
            mode='lines+markers',
            name='Pago Acumulado',
            line=dict(color='#2ecc71', width=3),
            marker=dict(size=8),
            hovertemplate="Data: %{x|%d/%m/%Y}<br>Valor Previsto: %{y:,.2f}<extra></extra>"
        ))
    fig_previsao.update_layout(
        title='Previsão x Pagamento Acumulado por Dia (Reset Mensal)',
        template="plotly_dark",
        paper_bgcolor="#2a2b4f",
        plot_bgcolor="#2a2b4f",
        font_color="white",
        xaxis_title="Data",
        yaxis_title="Valor (R$)",
        hovermode='x unified'
    )
    fig_previsao.update_xaxes(tickangle=-45, automargin=True)
    fig_previsao.update_yaxes(gridcolor='rgba(255,255,255,0.1)')

    # GRÁFICO : Tempo Médio entre Emissão e Pagamento + Percentual por Faixa
    if 'Emissão' in df_boletos.columns and 'Pagamento' in df_boletos.columns:
        df_boletos['Emissão'] = pd.to_datetime(df_boletos['Emissão'], format='%d/%m/%Y', errors='coerce')
        df_boletos['Pagamento'] = pd.to_datetime(df_boletos['Pagamento'], format='%d/%m/%Y', errors='coerce')
        df_validos = df_boletos.dropna(subset=['Emissão', 'Pagamento']).copy()
        if not df_validos.empty:
            df_validos['TempoPagamento'] = (df_validos['Pagamento'] - df_validos['Emissão']).dt.days
            df_validos['YearMonth'] = df_validos['Pagamento'].dt.to_period('M')
            if start_date and end_date:
                start_date_dt = pd.to_datetime(start_date).date()
                end_date_dt = pd.to_datetime(end_date).date()
                df_validos = df_validos[(df_validos['Pagamento'].dt.date >= start_date_dt) & 
                                        (df_validos['Pagamento'].dt.date <= end_date_dt)]
            df_tempo_medio = df_validos.groupby('YearMonth')['TempoPagamento'].mean().reset_index()
            df_tempo_medio['MesAno'] = df_tempo_medio['YearMonth'].dt.strftime('%b/%Y')
            fig_tempo_medio = px.line(
                df_tempo_medio,
                x='MesAno',
                y='TempoPagamento',
                title='Tempo Médio entre Emissão e Pagamento + Percentual por Faixa',
                markers=True,
                labels={'MesAno': 'Mês/Ano', 'TempoPagamento': 'Tempo Médio (dias)'},
                text=df_tempo_medio['TempoPagamento'].round(2).astype(str) + ' dias'
            )
            df_validos['FaixaPagamento'] = pd.cut(df_validos['TempoPagamento'],
                bins=[-float('inf'), 5, 10, float('inf')],
                labels=['0-5 dias', '6-10 dias', '10+ dias'],
                right=True,
                include_lowest=True
            )

            # Usa 'ValorFinal', que é mais confiável (vindo do merge com boletos)
            df_validos['ValorFinal'] = pd.to_numeric(df_validos['Valor'], errors='coerce')  # Se ainda não foi feito
            #df_validos.to_excel('df_validos.xlsx', index=False)
            # Soma o valor final pago por faixa e mês
            df_valores = df_validos.groupby(['YearMonth', 'FaixaPagamento'])['ValorFinal'].sum().reset_index(name='ValorPago')
           
            df_faixas = df_validos.groupby(['YearMonth', 'FaixaPagamento']).size().reset_index(name='Quantidade')
            
            df_totais = df_validos.groupby('YearMonth').size().reset_index(name='Total')
            
            df_faixas = df_faixas.merge(df_totais, on='YearMonth')
            
            df_faixas['Percentual'] = (df_faixas['Quantidade'] / df_faixas['Total']) * 100
            
            df_faixas['MesAno'] = df_faixas['YearMonth'].dt.strftime('%b/%Y')
            
            df_faixas = df_faixas.merge(df_valores, on=['YearMonth', 'FaixaPagamento'], how='left')
            

            fig_barras = px.bar(
                df_faixas,
                x='MesAno',
                y='Percentual',
                color='FaixaPagamento',
                barmode='overlay',
                category_orders={'FaixaPagamento': ['0-5 dias', '6-10 dias', '10+ dias']}
            )
            for trace in fig_barras.data:
                faixa = trace.name  # nome da faixa, ex.: '0-5 dias'
                # Cria uma lista de customdata alinhada com os x de cada barra na trace
                customdata_list = []
                for x_val in trace.x:
                    # Procura no DataFrame a linha que tenha o mesmo mês e a mesma faixa
                    row = df_faixas[(df_faixas['MesAno'] == x_val) & (df_faixas['FaixaPagamento'] == faixa)]
                    if not row.empty:
                        customdata_list.append([faixa, row.iloc[0]['ValorPago']])
                    else:
                        customdata_list.append([faixa, 0])
                trace.customdata = customdata_list
                trace.hovertemplate = (
                    'Mês: %{x}<br>' +
                    'Faixa: %{customdata[0]}<br>' +
                    'Percentual: %{y:.2f}%<br>' +
                    'Valor Pago: R$ %{customdata[1]:,.2f}<extra></extra>'
                )


            fig_tempo_medio = go.Figure()
            for trace in fig_barras.data:
                trace.yaxis = "y2"
                fig_tempo_medio.add_trace(trace)
            fig_tempo_medio.add_trace(go.Scatter(
                x=df_tempo_medio['MesAno'],
                y=df_tempo_medio['TempoPagamento'],
                mode='lines+markers',
                name='Tempo Médio de Pagamento',
                line=dict(color='#2ecc71', width=4),
                marker=dict(size=10),
                text=df_tempo_medio['TempoPagamento'].round(2).astype(str) + ' dias',
                textposition='top center'
            ))
            fig_tempo_medio.update_layout(
                title='Tempo Médio de Pagamento e Percentual por Faixa',
                template='plotly_dark',
                paper_bgcolor='#2a2b4f',
                plot_bgcolor='#2a2b4f',
                font_color='white',
                legend=dict(x=1.04, y=1),
                yaxis=dict(title='Tempo Médio (dias)'),
                yaxis2=dict(
                    title="Percentual de Pagamentos (%)",
                    overlaying="y",
                    side="right"
                ),
                barmode='stack'
            )
        else:
            fig_tempo_medio = go.Figure()
            fig_tempo_medio.update_layout(title='Tempo Médio entre Emissão e Pagamento - Sem Dados')
    else:
        fig_tempo_medio = go.Figure()
        fig_tempo_medio.update_layout(title='Tempo Médio entre Emissão e Pagamento - Dados Incompletos')



    # NOVO GRÁFICO: Quantidade de Empresas que Pagaram por Mês
    query_boletos = "SELECT Empresa, Pagamento FROM boletos_pago_v3"
    df_boletos = pd.read_sql(query_boletos, engine)
    df_boletos['Pagamento'] = pd.to_datetime(df_boletos['Pagamento'], format='%d/%m/%Y', errors='coerce')
    df_boletos.dropna(subset=['Pagamento'], inplace=True)

    # Aplica o filtro de data
    if start_date and end_date:
        start_date_dt = pd.to_datetime(start_date)
        end_date_dt = pd.to_datetime(end_date)
        df_boletos = df_boletos[(df_boletos['Pagamento'] >= start_date_dt) & (df_boletos['Pagamento'] <= end_date_dt)]

    # Cria uma coluna do tipo Period (mês/ano) para agrupar
    df_boletos['MesAno'] = df_boletos['Pagamento'].dt.to_period('M')

    # Agrupa por MesAno e conta o número de empresas únicas
    df_empresas_mes = df_boletos.groupby('MesAno')['Empresa'].nunique().reset_index(name='Quantidade')

    # Ordena pela coluna MesAno (agora em Period), garantindo ordem cronológica
    df_empresas_mes.sort_values('MesAno', inplace=True)

    # Cria uma coluna string formatada para exibir no eixo X (ex.: "Jan/2025")
    df_empresas_mes['MesAnoLabel'] = df_empresas_mes['MesAno'].dt.strftime('%b/%Y')

    # Monta o gráfico usando a coluna MesAnoLabel
    fig_pago_empresas = px.bar(
        df_empresas_mes,
        x='MesAnoLabel',
        y='Quantidade',
        title='Quantidade de Empresas que Pagaram por Mês',
        labels={'MesAnoLabel': 'Mês/Ano', 'Quantidade': 'Número de Empresas'}
    )
    fig_pago_empresas.update_layout(
    template="plotly_dark",
    paper_bgcolor="#2a2b4f",
    plot_bgcolor="#2a2b4f",
    font_color="white",
    xaxis=dict(type='category'),
    bargap=0.2
    )

    fig_pago_empresas.update_traces(marker_color='#38b6ff')


    # NOVO GRÁFICO: Ticket Médio por Mês
    query_ticket = "SELECT Empresa, Pagamento, Valor FROM boletos_pago_v3"
    df_ticket = pd.read_sql(query_ticket, engine)
    
    df_ticket['Pagamento'] = pd.to_datetime(df_ticket['Pagamento'], format='%d/%m/%Y', errors='coerce')
    df_ticket.dropna(subset=['Pagamento', 'Valor'], inplace=True)
    df_ticket['Valor'] = (
        df_ticket['Valor']
        .str.replace('R$', '', regex=False)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df_ticket['Valor'] = pd.to_numeric(df_ticket['Valor'], errors='coerce')
    
    # Aplica o filtro de data
    if start_date and end_date:
        start_date_dt = pd.to_datetime(start_date)
        end_date_dt = pd.to_datetime(end_date)
        df_ticket = df_ticket[(df_ticket['Pagamento'] >= start_date_dt) & (df_ticket['Pagamento'] <= end_date_dt)]
    
    # Agrupa por mês/ano
    df_ticket['MesAno'] = df_ticket['Pagamento'].dt.to_period('M')
    df_ticket_group = df_ticket.groupby('MesAno').agg(
        TotalValor=('Valor', 'sum'),
        Empresas=('Empresa', 'nunique')
    ).reset_index()
    df_ticket_group.sort_values('MesAno', inplace=True)
    df_ticket_group['MesAnoLabel'] = df_ticket_group['MesAno'].dt.strftime('%b/%Y')
    
    # Calcula o Ticket Médio: Total vendido / número de empresas únicas
    df_ticket_group['TicketMedio'] = df_ticket_group['TotalValor'] / df_ticket_group['Empresas']
    print(df_ticket_group)
    
    fig_ticket = px.bar(
        df_ticket_group,
        x='MesAnoLabel',
        y='TicketMedio',
        title='Ticket Médio por Mês',
        labels={'MesAnoLabel': 'Mês/Ano', 'TicketMedio': 'Ticket Médio (R$)'}
    )
    fig_ticket.update_layout(
        template="plotly_dark",
        paper_bgcolor="#2a2b4f",
        plot_bgcolor="#2a2b4f",
        font_color="white",
        xaxis=dict(type='category'),
        bargap=0.2
    )
    fig_ticket.update_traces(marker_color='#38b6ff')



    # GRÁFICO 5: Ranking das Empresas com Mais Atrasos de Pagamento (por quantidade)
    try:
        query_boletos = "SELECT * FROM boletos_pago_v3"
        df_boletos_emp = pd.read_sql(query_boletos, engine)
        df_boletos_emp['Emissão'] = pd.to_datetime(df_boletos_emp['Emissão'], format='%d/%m/%Y', errors='coerce')
        df_boletos_emp['Pagamento'] = pd.to_datetime(df_boletos_emp['Pagamento'], format='%d/%m/%Y', errors='coerce')
        df_boletos_emp.dropna(subset=['Emissão', 'Pagamento'], inplace=True)
        filtered_df['Nº Pedido'] = filtered_df['Nº Pedido'].astype(str).str.strip()
        df_boletos_emp['Número Pedido'] = df_boletos_emp['Número Pedido'].astype(str).str.strip()
        df_merged = pd.merge(
            filtered_df,
            df_boletos_emp,
            left_on='Nº Pedido',
            right_on='Número Pedido',
            how='inner',
            suffixes=('', '_boletos')
        )
        df_merged['TempoPagamento'] = (df_merged['Pagamento'] - df_merged['Emissão']).dt.days
        df_merged = df_merged[df_merged['TempoPagamento'] >= 0]
        df_atrasados = df_merged[df_merged['TempoPagamento'] > 5]
        if 'Empresa' in df_atrasados.columns:
            df_empresas = df_atrasados.groupby('Empresa').size().reset_index(name='QtdAtrasos')
            df_empresas = df_empresas.sort_values('QtdAtrasos', ascending=False).head(10)
        else:
            df_empresas = pd.DataFrame(columns=['Empresa', 'QtdAtrasos'])
        fig_empresas = px.bar(
            df_empresas,
            x='QtdAtrasos',
            y='Empresa',
            orientation='h',
            title='Top 10 Empresas com Mais Atrasos (Pagamento > 5 dias)',
            labels={'QtdAtrasos': 'Quantidade de Atrasos', 'Empresa': 'Empresa'}
        )
        fig_empresas.update_layout(
            template='plotly_dark',
            paper_bgcolor='#2a2b4f',
            plot_bgcolor='#2a2b4f',
            font_color='white'
        )
    except Exception as e:
        fig_empresas = go.Figure()
        fig_empresas.update_layout(title='Ranking de Empresas - Dados Indisponíveis')

    # GRÁFICO 6: Top 10 Empresas com Maiores Valores Devidos (Atraso > 5 dias)
    try:
        # Filtra os pedidos em status "Novo" (ainda não pagos) no período selecionado
        df_overdue = filtered_df[filtered_df['Status'] == 'Novo'].copy()
        hoje_normalizado = pd.Timestamp.now().normalize()
        df_overdue['DiasDesdePedido'] = (hoje_normalizado - df_overdue['Data do Pedido']).dt.days
        df_overdue = df_overdue[df_overdue['DiasDesdePedido'] > 5].copy()
        
        # Converter "Valor Crédito" para numérico
        if 'Valor Crédito' in df_overdue.columns:
            df_overdue['Valor Crédito'] = (
                df_overdue['Valor Crédito']
                .str.replace('R$', '', regex=False)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            df_overdue['Valor Crédito'] = pd.to_numeric(df_overdue['Valor Crédito'], errors='coerce')
        
        # Agrupar por "Empresa" e somar o valor devido
        df_devedores = df_overdue.groupby('Empresa', as_index=False)['Valor Crédito'].sum()
        df_devedores = df_devedores.sort_values('Valor Crédito', ascending=False).head(10)
        
        # Criar gráfico de barras horizontal
        fig_devedores = px.bar(
            df_devedores,
            x='Valor Crédito',
            y='Empresa',
            orientation='h',
            title='Top 10 Empresas com Maiores Valores Devidos (Atraso > 5 dias)',
            labels={'Valor Crédito': 'Valor Devido (R$)', 'Empresa': 'Empresa'}
        )
        fig_devedores.update_layout(
            template='plotly_dark',
            paper_bgcolor='#2a2b4f',
            plot_bgcolor='#2a2b4f',
            font_color='white'
        )
    except Exception as e:
        fig_devedores = go.Figure()
        fig_devedores.update_layout(title=f'Erro ao gerar gráfico de devedores: {e}')

    return (
        fig_conversao,
        fig_pago_empresas,
        fig_vencimento,
        fig_previsao,
        fig_tempo_medio,
        fig_empresas,
        fig_devedores,
        fig_vales,
        fig_ticket  
    )




# ----------------------------------------------------------------------------
# CALLBACK 2: Atualiza a tabela com os detalhes ao clicar no gráfico de vencidos
# ----------------------------------------------------------------------------
@app.callback(
    Output('table-vencidos', 'data'),
    [
        Input('graph-vencimento', 'clickData'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date')
    ]
)
def update_table_vencidos(clickData, start_date, end_date):
    if start_date and end_date:
        mask = (df_novo['Data do Pedido'] >= start_date) & (df_novo['Data do Pedido'] <= end_date)
        filtered_df = df_novo.loc[mask].copy()
    else:
        filtered_df = df_novo.copy()
    df_vencidos = filtrar_pedidos_vencidos(filtered_df)
    def categorize_vencimento(x):
        if x == 5:
            return "5 dias"
        elif 6 <= x <= 10:
            return "6 a 10 dias"
        elif 11 <= x < 30:
            return "11 a 29 dias"
        else:
            return None
    df_vencidos['FaixaVencimento'] = df_vencidos['DiasDesdePedido'].apply(categorize_vencimento)
    if not df_vencidos.empty and clickData is not None:
        faixa_clicada = clickData['points'][0]['x']
        df_filtrado = df_vencidos[df_vencidos['FaixaVencimento'] == faixa_clicada].copy()
        if not df_filtrado.empty:
            df_filtrado['Data do Pedido'] = df_filtrado['Data do Pedido'].dt.strftime('%d/%m/%Y')
        return df_filtrado.to_dict('records')
    else:
        return []
    
@app.callback(
    Output('table-devedores', 'data'),
    [
        Input('graph-evolucao', 'clickData'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date')
    ]
)
def update_table_devedores(clickData, start_date, end_date):
    # Filtra os dados pelo período selecionado
    if start_date and end_date:
        mask = (df_novo['Data do Pedido'] >= start_date) & (df_novo['Data do Pedido'] <= end_date)
        filtered_df = df_novo.loc[mask].copy()
    else:
        filtered_df = df_novo.copy()

    # Filtra os boletos com status "Novo" (ainda não pagos) e com atraso > 5 dias
    df_overdue = filtered_df[filtered_df['Status'] == 'Novo'].copy()
    hoje_normalizado = pd.Timestamp.now().normalize()
    df_overdue['DiasDesdePedido'] = (hoje_normalizado - df_overdue['Data do Pedido']).dt.days
    df_overdue = df_overdue[df_overdue['DiasDesdePedido'] > 5].copy()

    # Se houver clique no gráfico, filtra pelos boletos da empresa selecionada (eixo 'y')
    if clickData is not None:
        empresa_selecionada = clickData['points'][0]['y']
        df_filtrado = df_overdue[df_overdue['Empresa'] == empresa_selecionada].copy()
        if not df_filtrado.empty:
            df_filtrado['Data do Pedido'] = df_filtrado['Data do Pedido'].dt.strftime('%d/%m/%Y')
        return df_filtrado.to_dict('records')
    else:
        return []



@app.callback(
    Output("download-table-vencidos", "data"),  # Ação de download
    Input("btn-export-excel", "n_clicks"),      # Botão que dispara o download
    State("table-vencidos", "data"),            # Pega os dados atuais da tabela
    prevent_initial_call=True                   # Evita chamar sem ter clique
)
def export_table_vencidos(n_clicks, table_data):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    
    # Converte a lista de dicionários em DataFrame
    df = pd.DataFrame(table_data)

    # Retorna a ação de download
    return dcc.send_data_frame(
        df.to_excel,          # Função do pandas para salvar em Excel
        "Vencidos.xlsx",      # Nome do arquivo que o usuário fará download
        sheet_name="Vencidos" # Nome da planilha
    )



if __name__ == '__main__':
    app.run_server(debug=True, dev_tools_ui=False)
