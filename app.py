import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Comex.io | Light", page_icon="🚢", layout="wide")

# --- CSS LIGHT MODE (CLARO) ---
st.markdown("""
<style>
    /* Fundo Branco e Texto Escuro */
    .stApp { background-color: #f8f9fa; color: #212529; }
    
    /* Títulos em Azul Corporativo */
    h1, h2, h3 { color: #0d47a1 !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Cards de Métricas (Brancos com sombra suave) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] { color: #6c757d; font-weight: bold; }
    div[data-testid="stMetricValue"] { color: #0d47a1; }
    
    /* Ajuste de tabelas */
    div[data-testid="stDataFrame"] { border: 1px solid #dee2e6; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO DE DADOS DE SEGURANÇA (FALLBACK REALISTA) ---
def generate_fallback_data():
    """
    Gera dados simulados com valores ATUAIS de mercado (2025/26)
    para caso o Yahoo Finance bloqueie a conexão.
    """
    dates = pd.date_range(end=datetime.now(), periods=60, freq='B')
    n = len(dates)
    
    return pd.DataFrame({
        # Valores calibrados para o mercado atual (Dolar ~5.80, Yuan ~0.80)
        'Dolar': 5.80 + np.random.normal(0, 0.03, n).cumsum(),
        'Yuan': 0.80 + np.random.normal(0, 0.005, n).cumsum(),
        # Commodities
        'Soja': 1150 + np.random.normal(0, 8, n).cumsum(),
        'Petroleo': 70 + np.random.normal(0, 1.2, n).cumsum(),
        'Minerio': 60 + np.random.normal(0, 0.8, n).cumsum()
    }, index=dates)

# --- FUNÇÃO DE COLETA REAL ---
@st.cache_data(ttl=300)
def get_comex_data():
    tickers = {
        'Dolar': 'BRL=X',       # USD -> BRL
        'Yuan': 'CNYBRL=X',     # CNY -> BRL
        'Soja': 'ZS=F',         # Soja Futuro
        'Petroleo': 'CL=F',     # Petróleo WTI
        'Minerio': 'VALE3.SA'   # Vale (Proxy de Minério)
    }
    
    try:
        # Tenta baixar os últimos 5 dias (mais rápido e preciso)
        df = yf.download(list(tickers.values()), period="1mo", interval="1d", progress=False)
        
        if isinstance(df.columns, pd.MultiIndex):
            df = df['Close']
        
        if df.empty: return generate_fallback_data(), False

        # Renomeia colunas
        cols_existentes = {v: k for k, v in tickers.items() if v in df.columns}
        df = df[list(cols_existentes.keys())].rename(columns=cols_existentes)
        
        # Preenche colunas faltantes com valor fixo se necessário
        for nome_col in tickers.keys():
            if nome_col not in df.columns:
                df[nome_col] = 0.0
        
        df = df.ffill().dropna()
        
        if len(df) < 2: return generate_fallback_data(), False
        
        return df, True

    except Exception:
        return generate_fallback_data(), False

# --- CARGA E CÁLCULOS ---
df_market, is_real_data = get_comex_data()

# Seleção segura de datas
if len(df_market) >= 2:
    hoje = df_market.iloc[-1]
    ontem = df_market.iloc[-2]
    data_ref = df_market.index[-1].strftime('%d/%m/%Y')
else:
    # Caso extremo
    st.error("Erro crítico na base de dados.")
    st.stop()

# Cálculo Volume FOB (Estimado)
df_market['Volume_FOB_Mi'] = (df_market['Soja'] * 1.5) + (df_market['Petroleo'] * 2.0) + (df_market['Minerio'] * 5.0)
vol_hoje = df_market['Volume_FOB_Mi'].iloc[-1]
vol_ontem = df_market['Volume_FOB_Mi'].iloc[-2]

# Cálculo Destaque do Mês
idx_30d = -22 if len(df_market) >= 22 else 0
data_old = df_market.iloc[idx_30d]

ranking = {
    'Soja': (hoje['Soja'] - data_old['Soja']) / data_old['Soja'],
    'Petróleo': (hoje['Petroleo'] - data_old['Petroleo']) / data_old['Petroleo'],
    'Minério': (hoje['Minerio'] - data_old['Minerio']) / data_old['Minerio']
}
produto_top = max(ranking, key=ranking.get)
perf_top = ranking[produto_top] * 100

# --- DASHBOARD (LIGHT MODE) ---

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/container-truck.png", width=80)
    st.title("Comex.io")
    st.markdown("---")
    
    if is_real_data:
        st.success(f"🟢 Dados: Yahoo Finance\nRef: {data_ref}")
    else:
        st.warning(f"🟠 Dados: Estimativa de Mercado\nRef: {data_ref}")
        st.caption("Conexão instável. Usando valores projetados.")

# Cabeçalho
st.title(f"Painel de Exportação")
st.markdown(f"**Data de Referência:** {data_ref} | Monitoramento Estratégico")

# Cards (KPIs)
col1, col2, col3, col4 = st.columns(4)

def card_metric(col, label, valor, delta, prefix="R$ "):
    col.metric(label, f"{prefix}{valor:.3f}", f"{delta:.3f}")

with col1: card_metric(st, "🇺🇸 Dólar (PTAX/Com)", hoje['Dolar'], hoje['Dolar']-ontem['Dolar'])
with col2: card_metric(st, "🇨🇳 Yuan (CNY)", hoje['Yuan'], hoje['Yuan']-ontem['Yuan'])
with col3: card_metric(st, "📦 Vol. Diário (FOB)", vol_hoje, vol_hoje-vol_ontem, "US$ ")
with col4: st.metric("⭐ Destaque Mês", produto_top, f"{perf_top:.1f}%")

st.markdown("---")

# Gráficos (Tema Claro)
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📈 Evolução do Câmbio (USD/BRL)")
    # Gráfico de Linha Clean
    fig_line = px.line(df_market, y="Dolar", title="Tendência do Dólar (30 Dias)")
    
    # Ajuste para tema claro (Plotly White)
    fig_line.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#e9ecef'),
        font=dict(color="#333")
    )
    fig_line.update_traces(line_color='#0d47a1', line_width=3)
    st.plotly_chart(fig_line, use_container_width=True)

with c_right:
    st.subheader("🚢 Mix de Commodities")
    valores = [hoje['Soja'], hoje['Petroleo'], hoje['Minerio']]
    
    # Gráfico de Pizza Clean
    fig_pie = go.Figure(data=[go.Pie(
        labels=['Soja', 'Petróleo', 'Minério'], 
        values=valores, 
        hole=.5,
        marker=dict(colors=['#4caf50', '#2196f3', '#ff9800']) # Cores claras e distintas
    )])
    
    fig_pie.update_layout(
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", y=-0.1),
        margin=dict(t=0, b=0, l=0, r=0)
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# Tabela
st.markdown("---")
st.subheader("📋 Histórico Recente")

# Formatação da tabela para ficar bonita no tema claro
st.dataframe(
    df_market.tail(10).sort_index(ascending=False).style.format("{:.2f}"),
    use_container_width=True
)

# Download
csv = df_market.to_csv().encode('utf-8')
st.download_button("📥 Baixar Relatório (CSV)", csv, "comex_data.csv", "text/csv")
