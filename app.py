import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard Pizzaria - Estudo de Caso Nomad", layout="wide", page_icon="🍕")

# Cor Principal para os Gráficos
COR_PRINCIPAL = ['#FFC300'] # Amarelo Ouro

# --- CARREGAMENTO E LIMPEZA (ETL) ---
@st.cache_data
def carregar_dados():
    df_sales = pd.read_csv('pizza_sales.csv')
    df_types = pd.read_csv('pizza_types.csv')

    # LIMPEZA: Moeda
    if df_sales['unit_price'].dtype == 'object':
        df_sales['unit_price'] = df_sales['unit_price'].astype(str).str.replace(',', '.').astype(float)

    # LIMPEZA: Datas e Horas
    df_sales['order_date'] = pd.to_datetime(df_sales['order_date'], dayfirst=True, errors='coerce')
    df_sales['hora'] = pd.to_datetime(df_sales['order_time'], format='%H:%M:%S', errors='coerce').dt.hour

    df_sales['pizza_type_id'] = df_sales['pizza_name_id'].apply(lambda x: x.rsplit('_', 1)[0])

    # MERGE
    df_merged = pd.merge(df_sales, df_types, on='pizza_type_id', how='left')

    # KPI: Receita
    df_merged['receita_total'] = df_merged['quantity'] * df_merged['unit_price']

    return df_merged

try:
    df = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")
categorias = st.sidebar.multiselect(
    "Categoria",
    options=df['pizza_category'].unique(),
    default=df['pizza_category'].unique()
)

# Filtro de Data
data_min = df['order_date'].min()
data_max = df['order_date'].max()
periodo = st.sidebar.date_input("Período", [data_min, data_max])

if len(periodo) == 2:
    data_inicio, data_fim = periodo
    df_filtrado = df[
        (df['pizza_category'].isin(categorias)) &
        (df['order_date'] >= pd.to_datetime(data_inicio)) &
        (df['order_date'] <= pd.to_datetime(data_fim))
    ]
else:
    df_filtrado = df[df['pizza_category'].isin(categorias)]

# --- DASHBOARD ---

st.title("🍕 Dashboard Estratégico - Estudo de Caso Nomad")
st.markdown("---")

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Faturamento Total", f"R$ {df_filtrado['receita_total'].sum():,.2f}")
col2.metric("Pizzas Vendidas", f"{df_filtrado['quantity'].sum()}")
col3.metric("Pedidos Únicos", f"{df_filtrado['order_id'].nunique()}")
ticket_medio = df_filtrado['receita_total'].sum() / df_filtrado['order_id'].nunique() if df_filtrado['order_id'].nunique() > 0 else 0
col4.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")

st.markdown("---")

# Gráficos
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.subheader("🏆 Melhores Pizzas (Receita)")
    top_pizzas = df_filtrado.groupby('pizza_name')['receita_total'].sum().nlargest(5).reset_index()

    fig_top = px.bar(
        top_pizzas, 
        x='receita_total', 
        y='pizza_name', 
        orientation='h',
        template="plotly_dark",
        color_discrete_sequence=COR_PRINCIPAL
    )
    
    # Remove linhas de grade desnecessárias para visual limpo
    fig_top.update_layout(yaxis=dict(title=''), xaxis=dict(title='Receita ($)'))
    st.plotly_chart(fig_top, use_container_width=True)

with col_graf2:
    st.subheader("⚠️ Menor Venda (Risco)")
    pior_pizzas = df_filtrado.groupby('pizza_name')['quantity'].sum().nsmallest(5).reset_index()
    
    fig_low = px.bar(
        pior_pizzas, 
        x='quantity', 
        y='pizza_name', 
        orientation='h', 
        template="plotly_dark",
        color_discrete_sequence=['#555555'] 
    )
    fig_low.update_traces(marker_color='#FF5733')  # Tom laranja para destacar
    fig_low.update_layout(yaxis=dict(title=''), xaxis=dict(title='Qtd Vendida'))
    st.plotly_chart(fig_low, use_container_width=True)

col_1, col_2 = st.columns(2)

with col_1:
    # Curva Horário
    st.subheader("⏰ Picos de Horário")
    vendas_hora = df_filtrado.groupby('hora')['quantity'].sum().reset_index()

    fig_hora = px.line(
        vendas_hora,
        title="Curva de Demanda Horária",
        x='hora', 
        y='quantity', 
        labels={'hora': 'Hora do Dia', 'quantity': 'Pizzas Vendidas'},
        markers=True, 
        template="plotly_dark",
        color_discrete_sequence=COR_PRINCIPAL
    )

    fig_hora.update_layout(xaxis=dict(tickmode='linear', dtick=1))
    st.plotly_chart(fig_hora, use_container_width=True)

# Ticket Médio por Tamanho (Validação de Upsell)
with col_2:
    st.subheader("Performance Semanal")

    df_filtrado['dia_semana'] = df_filtrado['order_date'].dt.day_name()

    # Agrupa por dia e reordena
    vendas_dia = df_filtrado.groupby('dia_semana')['quantity'].sum().reindex(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    ).reset_index()

    fig_week = px.bar(vendas_dia, x='dia_semana', y='quantity',
                        title='Vendas por Dia da Semana',
                        labels={'dia_semana': 'Dia da Semana', 'quantity': 'Pizzas Vendidas'},
                        template="plotly_dark",
                        color_discrete_sequence=['#FFC300'])
    st.plotly_chart(fig_week, use_container_width=True)

st.markdown("---")

col_new1, col_new2 = st.columns(2)

# Análise de tamanho (Mix de Produto)
with col_new1:
    st.subheader("Preferência de Tamanho")
    # Agrupa por tamanho
    df_size = df_filtrado.groupby('pizza_size')['quantity'].sum().reset_index()
    
    # Ordem lógica dos tamanhos para o gráfico
    ordem_tamanhos = ['S', 'M', 'L', 'XL', 'XXL']
    
    fig_size = px.pie(df_size, values='quantity', names='pizza_size', 
                      title='Distribuição de Vendas por Tamanho',
                      template="plotly_dark",
                      hole=0.4) # Gráfico de Rosca
    st.plotly_chart(fig_size, use_container_width=True)

# Sazonalidade semanal
with col_new2:
    st.subheader("💰 Ticket Médio por Tamanho")

    df_ticket_tamanho = df_filtrado.groupby('pizza_size').agg({
        'receita_total': 'sum',
        'order_id': 'nunique'
    }).reset_index()

    df_ticket_tamanho['ticket_medio'] = df_ticket_tamanho['receita_total'] / df_ticket_tamanho['order_id']

    ordem_tamanhos = ['S', 'M', 'L', 'XL']

    fig_ticket_size = px.bar(
        df_ticket_tamanho, 
        x='pizza_size', 
        y='ticket_medio',
        text_auto='.2f',
        category_orders={'pizza_size': ordem_tamanhos}, # Força a ordem P, M, G...
        title="Ticket Médio por Tamanho (R$)",
        template="plotly_dark",
        color_discrete_sequence=['#FFC300'] 
    )

    # Ajustes visuais finais
    fig_ticket_size.update_traces(textfont_size=14, textangle=0, textposition="outside", cliponaxis=False)
    fig_ticket_size.update_layout(yaxis=dict(title='Ticket Médio ($)'), xaxis=dict(title='Tamanho'))

    st.plotly_chart(fig_ticket_size, use_container_width=True)

# Tamanho da Cesta (Oportunidade de Combo)
st.subheader("🛒 Comportamento do Cliente (Pizzas por Pedido)")
basket_size = df_filtrado.groupby('order_id')['quantity'].sum().reset_index()
basket_dist = basket_size['quantity'].value_counts().reset_index()
basket_dist.columns = ['qtd_pizzas_no_pedido', 'total_pedidos']

fig_basket = px.bar(basket_dist, x='qtd_pizzas_no_pedido', y='total_pedidos',
                    title='Quantas pizzas os clientes levam por vez?',
                    labels={'qtd_pizzas_no_pedido': 'Pizzas no Pedido', 'total_pedidos': 'Volume de Pedidos'},
                    template="plotly_dark",
                    text_auto=True,
                    color_discrete_sequence=['#FFC300'])
st.plotly_chart(fig_basket, use_container_width=True)

# Preço Médio por Tamanho
st.subheader("🏷️ Preço Médio Unitário (Quanto custa 1 pizza?)")

df_preco_medio = df_filtrado.groupby('pizza_size')['unit_price'].mean().reset_index()

ordem_tamanhos = ['S', 'M', 'L', 'XL', 'XXL']

# Criação do Gráfico
fig_price = px.bar(
    df_preco_medio, 
    x='pizza_size', 
    y='unit_price',
    title="Preço Médio da Pizza por Tamanho",
    labels={'unit_price': 'Preço Médio Unitário ($)', 'pizza_size': 'Tamanho'},
    category_orders={'pizza_size': ordem_tamanhos}, # Força a ordem P, M, G...
    template="plotly_dark",
    color_discrete_sequence=['#FFC300'], # Amarelo da identidade visual
    text_auto='.2f' # Mostra o valor com 2 casas decimais
)

fig_price.update_traces(textfont_size=14, textangle=0, textposition="outside", cliponaxis=False)
fig_price.update_layout(yaxis=dict(title='Preço ($)'), xaxis=dict(title='Tamanho'))

st.plotly_chart(fig_price, use_container_width=True)

# --- SIMULADOR DE PREÇIFICAÇÃO XL ---

st.markdown("---")
st.header("💸 Simulador de Impacto: Reajuste do Tamanho XL")
st.write("""
Como identificado, a pizza XL possui um preço médio desproporcionalmente baixo em relação ao tamanho L. 
Use o simulador abaixo para projetar o ganho de receita apenas ajustando este preço.
""")

# Filtrar apenas dados de XL
df_xl = df_filtrado[df_filtrado['pizza_size'] == 'XL'].copy()

# Calcular Métricas Atuais (Realizadas)
qtd_vendida_xl = df_xl['quantity'].sum()
faturamento_atual_xl = df_xl['receita_total'].sum()

# Evitar divisão por zero caso não haja vendas XL no filtro
if qtd_vendida_xl > 0:
    preco_medio_atual = faturamento_atual_xl / qtd_vendida_xl
else:
    preco_medio_atual = 0

# Interface de Simulação (Slider)
col_sim1, col_sim2 = st.columns([1, 2])

with col_sim1:
    st.subheader("Parâmetros")
    aumento_pct = st.slider("Percentual de Aumento Sugerido (%)", min_value=0, max_value=50, value=15, step=1)
    
    # Cálculo do Novo Preço
    novo_preco_medio = preco_medio_atual * (1 + (aumento_pct / 100))
    st.info(f"Preço Médio Atual: **R$ {preco_medio_atual:.2f}**")
    st.warning(f"Novo Preço Simulado: **R$ {novo_preco_medio:.2f}**")

with col_sim2:
    st.subheader("Projeção de Resultado")
    
    # Cálculo do Novo Faturamento (Mantendo o volume de vendas constante - Elasticidade Inelástica assumida)
    faturamento_projetado = qtd_vendida_xl * novo_preco_medio
    ganho_extra = faturamento_projetado - faturamento_atual_xl
    
    # Exibição dos Cartões Métricos
    col_metric1, col_metric2 = st.columns(2)
    
    col_metric1.metric(
        label="Faturamento Atual (XL)",
        value=f"R$ {faturamento_atual_xl:,.2f}"
    )
    
    col_metric2.metric(
        label="Novo Faturamento Projetado",
        value=f"R$ {faturamento_projetado:,.2f}",
        delta=f"+ R$ {ganho_extra:,.2f} (Ganho Líquido)"
    )
    
    st.caption("*Considerando manutenção do volume de vendas atual.")

# Gráfico Comparativo Rápido
dados_simulacao = pd.DataFrame({
    'Cenário': ['Atual', 'Simulado'],
    'Faturamento': [faturamento_atual_xl, faturamento_projetado]
})

fig_sim = px.bar(dados_simulacao, x='Faturamento', y='Cenário', orientation='h', 
                 title="Impacto Direto no Caixa", text_auto='.2s',
                 template="plotly_dark", color='Cenário', 
                 color_discrete_map={'Atual': '#555555', 'Simulado': '#00C851'}) # Verde para o ganho

st.plotly_chart(fig_sim, use_container_width=True)