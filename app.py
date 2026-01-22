import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard Pizzaria - Estudo de Caso", layout="wide", page_icon="🍕")

# --- ESTILO PERSONALIZADO (CSS) ---
# Força o fundo escuro nos elementos nativos e texto amarelo
st.markdown("""
    <style>
    /* Títulos em Amarelo */
    h1, h2, h3, .css-10trblm {
        color: #000 !important;
    }
    /* Métricas (Números grandes) em Amarelo */
    div[data-testid="stMetricValue"] {
        color: #000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Cor Principal para os Gráficos
COR_PRINCIPAL = ['#FFC300'] # Amarelo Ouro

# --- 1. CARREGAMENTO E LIMPEZA (ETL) ---
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

# --- 2. BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")
categorias = st.sidebar.multiselect(
    "Categoria",
    options=df['pizza_category'].unique(),
    default=df['pizza_category'].unique()
)

# Filtro de Data (Correção do erro de Comprimento)
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

# --- 3. DASHBOARD (LAYOUT AMARELO/PRETO) ---

st.title("🍕 Dashboard Estratégico")
st.markdown("---")

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Faturamento Total", f"R$ {df_filtrado['receita_total'].sum():,.2f}")
col2.metric("Pizzas Vendidas", f"{df_filtrado['quantity'].sum()}")
col3.metric("Pedidos Únicos", f"{df_filtrado['order_id'].nunique()}")
ticket_medio = df_filtrado['receita_total'].sum() / df_filtrado['order_id'].nunique() if df_filtrado['order_id'].nunique() > 0 else 0
col4.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")

st.markdown("---")

# GRÁFICOS
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.subheader("🏆 Melhores Pizzas (Receita)")
    top_pizzas = df_filtrado.groupby('pizza_name')['receita_total'].sum().nlargest(5).reset_index()
    
    # Configuração Visual: Fundo Preto (plotly_dark) e Barras Amarelas
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
        color_discrete_sequence=['#555555'] # Cinza para indicar baixa performance (ou use amarelo se preferir)
    )
    fig_low.update_traces(marker_color='#FFC300') # Forçando amarelo também aqui
    fig_low.update_layout(yaxis=dict(title=''), xaxis=dict(title='Qtd Vendida'))
    st.plotly_chart(fig_low, use_container_width=True)

# Curva Horária
st.subheader("⏰ Picos de Horário")
vendas_hora = df_filtrado.groupby('hora')['quantity'].sum().reset_index()

fig_hora = px.line(
    vendas_hora, 
    x='hora', 
    y='quantity', 
    markers=True, 
    template="plotly_dark",
    color_discrete_sequence=COR_PRINCIPAL
)
fig_hora.update_layout(xaxis=dict(tickmode='linear', dtick=1))
st.plotly_chart(fig_hora, use_container_width=True)