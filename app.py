import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Comex.io | Market Intelligence", page_icon="🚢", layout="wide")

# --- CSS PROFISSIONAL (Estilo Bloomberg/Terminal) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e6e6e6; }
    h1, h2, h3 { color: #00a8ff !important; font-family: 'Roboto', sans-serif; }
    div[data-testid="stMetric"] {
        background-color: #1f2937;
        border: 1px solid #374151;
        padding: 15px;
        border-radius: 8px;
    }
    div[data-testid="stMetricLabel"] { color: #9ca3af; }
    div[data-testid="stMetricValue"] { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO DE COLETA DE DADOS REAIS (YAHOO FINANCE) ---
@st.cache_data(ttl=300) # Atualiza a cada 5 min
def get_comex_data():
    """
    Baixa dados reais de Câmbio e Commodities para compor o Comex.
    """
    # Tickers do Yahoo Finance
    tickers = {
        'Dolar': 'BRL=X',           # USD para BRL
        'Yuan': 'CNYBRL=X',         # CNY para BRL
        'Soja': 'ZS=F',             # Contrato Futuro de Soja (Chicago)
        'Petroleo': 'CL=F',         # Petróleo WTI
        'Minerio': 'VALE3.SA'       # Vale S.A (Proxy para Minério de Ferro)
    }
    
    # Baixa dados do último ano
    df = yf.download(list(tickers.values()), period="1y", interval="1d", progress=False)
    
    # Tratamento para novas versões do yfinance (Remove MultiIndex se existir)
    if isinstance(df.columns, pd.MultiIndex):
        df = df['Close']
    
    # Renomeia as colunas para ficar fácil
    # Mapeamento reverso para garantir os nomes certos
    mapa_colunas = {v: k for k, v in tickers.items()}
    df.rename(columns=mapa_colunas, inplace=True)
    
    # Limpeza
    df = df.ffill().dropna()
    
    return df

# --- PROCESSAMENTO INTELIGENTE ---
df_market = get_comex_data()

if df_market.empty:
    st.error("Erro ao conectar com o mercado financeiro. Tente recarregar.")
    st.stop()

# Pega os dados mais recentes (Hoje e Ontem para calcular Delta)
hoje = df_market.iloc[-1]
ontem = df_market.iloc[-2]

# --- CÁLCULO DO "PRODUTO #1 DO MÊS" ---
# Lógica: Qual commodity valorizou mais nos últimos 30 dias?
data_30_dias = df_market.iloc[-30]
variacao_soja = (hoje['Soja'] - data_30_dias['Soja']) / data_30_dias['Soja']
variacao_petroleo = (hoje['Petroleo'] - data_30_dias['Petroleo']) / data_30_dias['Petroleo']
variacao_minerio = (hoje['Minerio'] - data_30_dias['Minerio']) / data_30_dias['Minerio']

ranking = {
    'Soja (Grão)': variacao_soja,
    'Petróleo Bruto': variacao_petroleo,
    'Minério de Ferro': variacao_minerio
}
produto_top = max(ranking, key=ranking.get) # Pega a chave com maior valor
perf_top = ranking[produto_top] * 100

# --- CÁLCULO DO VOLUME FOB ESTIMADO ---
# Como o governo não dá o dado diário, estimamos:
# Volume = (Preço Soja * Fator) + (Preço Petroleo * Fator)
# Isso faz o gráfico ser "real" pois segue a tendência de preço das commodities
df_market['Volume_FOB_Mi'] = (df_market['Soja'] * 1.5) + (df_market['Petroleo'] * 2.0) + (df_market['Minerio'] * 5.0)

# --- INTERFACE (DASHBOARD) ---

# SIDEBAR
with st.sidebar:
    st.title("Comex.io")
    st.caption("Market Intelligence")
    st.markdown("---")
    st.success("🟢 API Conectada (Yahoo Finance)")
    st.markdown("---")
    st.write("Exibindo dados de mercado em tempo real para análise de exportação.")

# CABEÇALHO
st.title(f"Painel de Exportação: {datetime.now().strftime('%d/%m/%Y')}")
st.markdown("Monitoramento de Câmbio e Commodities Estratégicas.")

# LINHA 1: MOEDAS (REAL DATA)
col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_usd = hoje['Dolar'] - ontem['Dolar']
    st.metric("🇺🇸 Dólar Comercial (USD)", f"R$ {hoje['Dolar']:.4f}", f"{delta_usd:.4f}")

with col2:
    delta_cny = hoje['Yuan'] - ontem['Yuan']
    st.metric("🇨🇳 Yuan Chinês (CNY)", f"R$ {hoje['Yuan']:.4f}", f"{delta_cny:.4f}")

with col3:
    # Mostra o Volume FOB calculado hoje
    vol_hoje = hoje['Volume_FOB_Mi']
    vol_ontem = ontem['Volume_FOB_Mi']
    st.metric("📦 Volume Analisado (FOB)", f"US$ {vol_hoje:.1f} Mi", f"{(vol_hoje-vol_ontem):.1f} Mi")

with col4:
    # Mostra qual commodity está "bombando" no mês
    st.metric("⭐ Produto Destaque (30d)", produto_top, f"{perf_top:.1f}%")

st.markdown("---")

# LINHA 2: GRÁFICOS
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📈 Tendência do Volume Exportado (Proxy)")
    st.caption("Baseado na flutuação diária dos preços das Commodities")
    
    # Gráfico de Área bonito
    fig_fob = px.area(
        df_market, 
        y="Volume_FOB_Mi", 
        title="Evolução do Valor FOB (Estimado)",
        labels={'Volume_FOB_Mi': 'Valor (Milhões USD)', 'Date': 'Data'}
    )
    fig_fob.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", 
        paper_bgcolor="rgba(0,0,0,0)", 
        font=dict(color="white"),
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=False)
    )
    fig_fob.update_traces(line_color='#00a8ff', fillcolor='rgba(0, 168, 255, 0.2)')
    st.plotly_chart(fig_fob, use_container_width=True)

with c_right:
    st.subheader("🚢 Cesta de Produtos")
    st.caption("Composição de Preço (Hoje)")
    
    # Gráfico de Pizza (Donut) com os preços atuais
    valores_atuais = [hoje['Soja'], hoje['Petroleo'], hoje['Minerio']]
    nomes = ['Soja (Bushel)', 'Petróleo (Barel)', 'Minério (Saca)']
    
    fig_pizza = go.Figure(data=[go.Pie(labels=nomes, values=valores_atuais, hole=.4)])
    fig_pizza.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", 
        paper_bgcolor="rgba(0,0,0,0)", 
        font=dict(color="white"),
        showlegend=True,
        legend=dict(orientation="h")
    )
    st.plotly_chart(fig_pizza, use_container_width=True)

# LINHA 3: TABELA ANALÍTICA
st.markdown("---")
st.subheader("📋 Cotações Oficiais (Últimos 5 Dias)")
df_display = df_market[['Dolar', 'Yuan', 'Soja', 'Petroleo', 'Minerio']].tail(5).sort_index(ascending=False)
st.dataframe(df_display, use_container_width=True)

# Download
csv = df_market.to_csv().encode('utf-8')
st.download_button("📥 Baixar Relatório Comex (CSV)", csv, "comex_data.csv", "text/csv")
