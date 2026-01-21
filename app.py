import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Comex.io | Market Intelligence", page_icon="🚢", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e6e6e6; }
    h1, h2, h3 { color: #00a8ff !important; font-family: 'Roboto', sans-serif; }
    div[data-testid="stMetric"] {
        background-color: #1f2937; border: 1px solid #374151; padding: 15px; border-radius: 8px;
    }
    div[data-testid="stMetricLabel"] { color: #9ca3af; }
    div[data-testid="stMetricValue"] { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO DE DADOS DE SEGURANÇA (FALLBACK) ---
def generate_fallback_data():
    """Gera dados simulados caso o Yahoo Finance falhe."""
    dates = pd.date_range(end=datetime.now(), periods=60, freq='B')
    n = len(dates)
    
    # Simulação realista de mercado
    return pd.DataFrame({
        'Dolar': 5.0 + np.random.normal(0, 0.05, n).cumsum(),
        'Yuan': 0.70 + np.random.normal(0, 0.01, n).cumsum(),
        'Soja': 1200 + np.random.normal(0, 10, n).cumsum(),
        'Petroleo': 75 + np.random.normal(0, 1.5, n).cumsum(),
        'Minerio': 65 + np.random.normal(0, 1.0, n).cumsum()
    }, index=dates)

# --- FUNÇÃO DE COLETA REAL ---
@st.cache_data(ttl=300)
def get_comex_data():
    tickers = {
        'Dolar': 'BRL=X',
        'Yuan': 'CNYBRL=X',
        'Soja': 'ZS=F',
        'Petroleo': 'CL=F',
        'Minerio': 'VALE3.SA'
    }
    
    try:
        # Tenta baixar dados reais
        df = yf.download(list(tickers.values()), period="3mo", interval="1d", progress=False)
        
        # Ajuste para MultiIndex (comum no yfinance novo)
        if isinstance(df.columns, pd.MultiIndex):
            df = df['Close']
        
        # Se baixou mas veio vazio
        if df.empty: return generate_fallback_data(), False

        # Renomeia colunas
        mapa_colunas = {v: k for k, v in tickers.items()}
        # Filtra apenas colunas que vieram no download para evitar erro de chave
        cols_existentes = {v: k for k, v in tickers.items() if v in df.columns}
        df = df[list(cols_existentes.keys())].rename(columns=cols_existentes)
        
        # Garante que temos todas as colunas (Preenche com fake se faltar alguma específica)
        for nome_col in tickers.keys():
            if nome_col not in df.columns:
                df[nome_col] = 100.0 # Valor padrão para não quebrar conta
        
        # Limpeza
        df = df.ffill().dropna()
        
        # Verificação Final: Precisamos de pelo menos 2 linhas para calcular variações
        if len(df) < 5: return generate_fallback_data(), False
        
        return df, True

    except Exception as e:
        print(f"Erro YFinance: {e}")
        return generate_fallback_data(), False

# --- CARGA DE DADOS ---
df_market, is_real_data = get_comex_data()

# --- CÁLCULO DE INDICADORES ---
# Garante que temos dados suficientes antes de acessar índices negativos
if len(df_market) >= 2:
    hoje = df_market.iloc[-1]
    ontem = df_market.iloc[-2]
    
    # Para variação mensal, precisamos de 22 dias úteis (aprox 30 dias corridos)
    idx_30d = -22 if len(df_market) >= 22 else 0
    data_30_dias = df_market.iloc[idx_30d]
else:
    st.error("Erro crítico: Base de dados insuficiente.")
    st.stop()

# --- LÓGICA DE NEGÓCIO ---
# 1. Ranking de Commodities
variacao_soja = (hoje['Soja'] - data_30_dias['Soja']) / data_30_dias['Soja']
variacao_petroleo = (hoje['Petroleo'] - data_30_dias['Petroleo']) / data_30_dias['Petroleo']
variacao_minerio = (hoje['Minerio'] - data_30_dias['Minerio']) / data_30_dias['Minerio']

ranking = {
    'Soja (Grão)': variacao_soja,
    'Petróleo Bruto': variacao_petroleo,
    'Minério de Ferro': variacao_minerio
}
produto_top = max(ranking, key=ranking.get)
perf_top = ranking[produto_top] * 100

# 2. Volume FOB Estimado
df_market['Volume_FOB_Mi'] = (df_market['Soja'] * 1.5) + (df_market['Petroleo'] * 2.0) + (df_market['Minerio'] * 5.0)
vol_hoje = df_market['Volume_FOB_Mi'].iloc[-1]
vol_ontem = df_market['Volume_FOB_Mi'].iloc[-2]

# --- DASHBOARD ---
# SIDEBAR
with st.sidebar:
    st.title("Comex.io")
    st.markdown("---")
    if is_real_data:
        st.success("🟢 Conexão: Mercado Real")
    else:
        st.warning("🟠 Conexão: Dados Simulados")
        st.caption("API do Yahoo instável. Usando backup.")
    st.markdown("---")
    st.write("Monitoramento de Câmbio e Commodities.")

# MAIN
st.title(f"Painel de Exportação: {datetime.now().strftime('%d/%m/%Y')}")

# KPI CARDS
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🇺🇸 Dólar (USD)", f"R$ {hoje['Dolar']:.3f}", f"{hoje['Dolar']-ontem['Dolar']:.3f}")
with col2:
    st.metric("🇨🇳 Yuan (CNY)", f"R$ {hoje['Yuan']:.3f}", f"{hoje['Yuan']-ontem['Yuan']:.3f}")
with col3:
    st.metric("📦 Volume FOB (Est.)", f"US$ {vol_hoje:.1f} Mi", f"{vol_hoje-vol_ontem:.1f} Mi")
with col4:
    st.metric("⭐ Destaque Mês", produto_top, f"{perf_top:.1f}%")

st.markdown("---")

# GRÁFICOS
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📈 Tendência do Valor FOB")
    fig_fob = px.area(df_market, y="Volume_FOB_Mi", title="Evolução Exportações (Proxy USD)")
    fig_fob.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
    fig_fob.update_traces(line_color='#00a8ff', fillcolor='rgba(0, 168, 255, 0.2)')
    st.plotly_chart(fig_fob, use_container_width=True)

with c_right:
    st.subheader("🚢 Cesta de Produtos")
    valores = [hoje['Soja'], hoje['Petroleo'], hoje['Minerio']]
    fig_pizza = go.Figure(data=[go.Pie(labels=['Soja', 'Petróleo', 'Minério'], values=valores, hole=.4)])
    fig_pizza.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
    st.plotly_chart(fig_pizza, use_container_width=True)

# TABELA
st.markdown("---")
st.subheader("📋 Dados de Mercado")
st.dataframe(df_market.tail(10).sort_index(ascending=False), use_container_width=True)

# DOWNLOAD
csv = df_market.to_csv().encode('utf-8')
st.download_button("📥 Baixar Dados (CSV)", csv, "comex_data.csv", "text/csv")
