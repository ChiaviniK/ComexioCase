import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- Configuração "Maritime Logistics" ---
st.set_page_config(page_title="Comex.io | Trade Radar", page_icon="🚢", layout="wide")

st.markdown("""
<style>
    /* Cores: Navy Blue (Oceano) e Gold (Dinheiro) */
    .stApp { background-color: #f0f2f6; color: #1e293b; }
    
    /* Header */
    h1, h2, h3 { color: #0f172a !important; font-family: 'Helvetica Neue', sans-serif; }
    
    /* Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-left: 5px solid #d4af37; /* Gold */
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Tabelas */
    .stDataFrame { border: 1px solid #cbd5e1; }
    
    /* Botões */
    .stButton>button {
        background-color: #0f172a; color: white; border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- DICIONÁRIO NCM (Simulação para deixar legível) ---
NCM_MAP = {
    '85171300': 'Smartphones',
    '84713012': 'Tablets/iPads',
    '95030097': 'Brinquedos (Outros)',
    '39241000': 'Utensílios Plásticos (Stanley?)',
    '61091000': 'Camisetas Algodão',
    '87116000': 'Scooters Elétricas',
    '85094010': 'Liquidificadores',
    '90183929': 'Equipamentos Médicos'
}

# --- FUNÇÕES DE API (REAL-TIME ECONOMY) ---

@st.cache_data(ttl=60)
def get_exchange_rates():
    """Busca Dólar e Yuan em tempo real (AwesomeAPI)"""
    try:
        # USD-BRL e CNY-BRL
        url = "https://economia.awesomeapi.com.br/last/USD-BRL,CNY-BRL"
        r = requests.get(url, timeout=5)
        data = r.json()
        
        return {
            'USD': float(data['USDBRL']['bid']),
            'CNY': float(data['CNYBRL']['bid']),
            'USD_VAR': float(data['USDBRL']['pctChange']),
            'CNY_VAR': float(data['CNYBRL']['pctChange'])
        }
    except:
        # Fallback se API cair
        return {'USD': 5.00, 'CNY': 0.70, 'USD_VAR': 0.0, 'CNY_VAR': 0.0}

# --- FUNÇÃO GERADORA DE DADOS (COMEX STAT SIMULADO) ---
@st.cache_data
def load_comex_data():
    """
    Simula um CSV do MDIC com movimentação de importação.
    Colunas típicas do Comex Stat: CO_NCM, NO_NCM, VL_FOB, KG_LIQUIDO, SG_UF_NCM
    """
    data = []
    # Gera dados para 3 meses
    ncms = list(NCM_MAP.keys())
    portos = ['Santos', 'Paranaguá', 'Itajaí', 'Suape', 'Manaus']
    paises = ['China', 'China', 'China', 'Estados Unidos', 'Estados Unidos', 'Alemanha', 'Vietnã']
    
    for _ in range(500):
        ncm = random.choice(ncms)
        porto = random.choice(portos)
        pais = random.choice(paises)
        
        # Lógica de tendência: "Scooters" e "Copos" explodindo recentemente
        fator_tendencia = 1.0
        if ncm in ['87116000', '39241000']: # Scooter e Copos
            fator_tendencia = random.uniform(1.5, 3.0) 
            
        valor = random.uniform(10000, 500000) * fator_tendencia
        peso = valor / random.uniform(5, 50) # Preço por kg varia
        
        data.append({
            'CO_NCM': ncm,
            'Produto': NCM_MAP[ncm],
            'Valor_FOB_USD': valor,
            'Peso_KG': peso,
            'Porto_Entrada': porto,
            'Pais_Origem': pais,
            'Data': random.choice(['2024-01-01', '2024-02-01', '2024-03-01']) # Trimestre
        })
        
    df = pd.DataFrame(data)
    # Calcula preço médio por KG (Proxy de Custo)
    df['Preco_Medio_KG'] = df['Valor_FOB_USD'] / df['Peso_KG']
    return df

import random # Necessário para o mock

# --- CARGA ---
rates = get_exchange_rates()
df_comex = load_comex_data()

# --- SIDEBAR ---
with st.sidebar:
    st.title("Comex.io")
    st.image("https://img.icons8.com/color/96/container-truck.png", width=80)
    st.markdown("---")
    
    st.subheader("Filtros de Inteligência")
    selected_origin = st.multiselect("Origem:", df_comex['Pais_Origem'].unique(), default=['China', 'Estados Unidos'])
    selected_port = st.multiselect("Porto de Entrada:", df_comex['Porto_Entrada'].unique(), default=['Santos', 'Paranaguá'])
    
    st.markdown("---")
    st.info("Dados baseados no Comex Stat (MDIC) + Cotações AwesomeAPI.")

# Aplica filtros
if selected_origin:
    df_filtered = df_comex[df_comex['Pais_Origem'].isin(selected_origin)]
else:
    df_filtered = df_comex

if selected_port:
    df_filtered = df_filtered[df_filtered['Porto_Entrada'].isin(selected_port)]

# --- INTERFACE PRINCIPAL ---
st.title("RADAR DE TENDÊNCIAS DE IMPORTAÇÃO")

# 1. Ticker Financeiro (Live API)
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Dólar Comercial (USD)", f"R$ {rates['USD']:.3f}", f"{rates['USD_VAR']}%")
with c2:
    st.metric("Yuan Chinês (CNY)", f"R$ {rates['CNY']:.3f}", f"{rates['CNY_VAR']}%")
with c3:
    vol_total = df_filtered['Valor_FOB_USD'].sum()
    st.metric("Volume Analisado (FOB)", f"US$ {vol_total/1000000:.1f} M")
with c4:
    top_prod = df_filtered.groupby('Produto')['Valor_FOB_USD'].sum().idxmax()
    st.metric("Produto #1 do Mês", top_prod)

st.markdown("---")

# 2. O CORAÇÃO DO CASE: Detecção de Tendência (Growth Hacking)
st.subheader("🔥 Produtos em Explosão (Trending Alert)")
st.caption("Produtos com crescimento de volume acima da média no último trimestre.")

# Lógica de Agrupamento
df_trend = df_filtered.groupby(['Produto', 'Data'])['Valor_FOB_USD'].sum().reset_index()
# Pivot para comparar meses
df_pivot = df_trend.pivot(index='Produto', columns='Data', values='Valor_FOB_USD').fillna(0)

# Simulação de Crescimento (Cálculo simples Last Month vs First Month)
colunas_data = sorted(df_pivot.columns)
if len(colunas_data) >= 2:
    inicio = colunas_data[0]
    fim = colunas_data[-1]
    df_pivot['Crescimento_%'] = ((df_pivot[fim] - df_pivot[inicio]) / df_pivot[inicio]) * 100
    
    # Filtra Top 5 Crescimento
    df_hot = df_pivot.sort_values('Crescimento_%', ascending=False).head(5)
    
    # Gráfico de Barras Horizontal
    fig_trend = px.bar(
        df_hot, x='Crescimento_%', y=df_hot.index, orientation='h',
        color='Crescimento_%', color_continuous_scale='Bluered',
        title=f"Top Produtos Ganhando Tração ({inicio} vs {fim})"
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.warning("Dados insuficientes para cálculo de tendência.")

# 3. Análise Geográfica e Logística
c_map, c_port = st.columns([2, 1])

with c_map:
    st.subheader("🗺️ Origem das Importações")
    df_map = df_filtered.groupby('Pais_Origem')['Valor_FOB_USD'].sum().reset_index()
    fig_map = px.choropleth(
        df_map, locations="Pais_Origem", locationmode="country names",
        color="Valor_FOB_USD", hover_name="Pais_Origem",
        color_continuous_scale="Blues", projection="natural earth"
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

with c_port:
    st.subheader("⚓ Gargalos Logísticos")
    df_port = df_filtered['Porto_Entrada'].value_counts().reset_index()
    df_port.columns = ['Porto', 'Qtd_Cargas']
    fig_pie = px.pie(df_port, values='Qtd_Cargas', names='Porto', hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

# 4. Tabela Analítica (Download)
st.subheader("📋 Detalhamento por NCM (Data Mining)")
st.dataframe(df_filtered.sort_values('Valor_FOB_USD', ascending=False).head(10), use_container_width=True)

csv = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button("📥 Baixar Base Filtrada (CSV)", csv, "comex_trend_data.csv", "text/csv")
