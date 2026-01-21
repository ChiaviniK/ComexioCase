import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="E-Comex Tracker", page_icon="🛍️", layout="wide")

# --- CSS LIGHT MODE ---
st.markdown("""
<style>
    .stApp { background-color: #f5f5f7; color: #1d1d1f; }
    h1, h2, h3 { color: #0071e3 !important; font-family: 'Helvetica Neue', sans-serif; }
    div[data-testid="stMetric"] {
        background-color: white; border-radius: 12px; padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e5e5;
    }
    div[data-testid="stImage"] img { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO 1: CÂMBIO REAL (AWESOME API) ---
@st.cache_data(ttl=60) # Atualiza a cada 1 min
def get_real_currency():
    """
    Pega a cotação oficial e atualizada via AwesomeAPI (Melhor que Yahoo para BRL).
    """
    # USD-BRL e CNY-BRL (Yuan)
    url = "https://economia.awesomeapi.com.br/last/USD-BRL,CNY-BRL"
    
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            return {
                'Dolar': float(data['USDBRL']['bid']),
                'Dolar_Var': float(data['USDBRL']['pctChange']),
                'Yuan': float(data['CNYBRL']['bid']),
                'Yuan_Var': float(data['CNYBRL']['pctChange']),
                'Time': datetime.now().strftime("%H:%M")
            }
    except:
        pass
    
    # Fallback de emergência (mas a AwesomeAPI raramente falha)
    return {'Dolar': 5.35, 'Dolar_Var': 0.0, 'Yuan': 0.75, 'Yuan_Var': 0.0, 'Time': 'N/A'}

# --- FUNÇÃO 2: PRODUTOS REAIS (MERCADO LIVRE API) ---
@st.cache_data(ttl=300)
def get_ml_products(query):
    """
    Busca produtos reais no Mercado Livre Brasil.
    """
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={query}&limit=20"
    
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            products = []
            
            for item in data['results']:
                products.append({
                    'Foto': item['thumbnail'],
                    'Produto': item['title'],
                    'Preço (R$)': item['price'],
                    'Link': item['permalink']
                })
            
            return pd.DataFrame(products)
    except:
        pass
    return pd.DataFrame()

# --- CARGA DE DADOS ---
cambio = get_real_currency()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/3d-fluency/96/box.png", width=80)
    st.title("E-Comex")
    st.caption("Importação & Revenda")
    st.markdown("---")
    
    # Seletor de Categoria
    categoria = st.selectbox(
        "📦 O que vamos importar?",
        ["Xiaomi Redmi", "Drone DJI", "Fones Bluetooth", "Smartwatch", "Alexa Echo"]
    )
    
    st.info(f"Cotação Atualizada às {cambio['Time']}")

# --- DASHBOARD ---
st.title(f"Monitor de Importação: {categoria}")

# 1. LINHA DO CÂMBIO (MOEDAS)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🇺🇸 Dólar Hoje", f"R$ {cambio['Dolar']:.3f}", f"{cambio['Dolar_Var']}%")
with col2:
    st.metric("🇨🇳 Yuan Chinês", f"R$ {cambio['Yuan']:.3f}", f"{cambio['Yuan_Var']}%")

# Busca Produtos
df_prod = get_ml_products(categoria)

if not df_prod.empty:
    media_preco = df_prod['Preço (R$)'].mean()
    min_preco = df_prod['Preço (R$)'].min()
    
    # Estimativa de Custo na China (Chutando 40% do valor Brasil)
    custo_china_usd = (media_preco * 0.40) / cambio['Dolar']
    
    with col3:
        st.metric("🇧🇷 Preço Médio Brasil", f"R$ {media_preco:.2f}")
    with col4:
        st.metric("🇨🇳 Custo Est. China (FOB)", f"US$ {custo_china_usd:.2f}", help="Estimado em 40% do valor de venda")

    st.markdown("---")

    # 2. ANÁLISE VISUAL E TABELA
    c_chart, c_table = st.columns([1, 2])
    
    with c_chart:
        st.subheader("📊 Distribuição de Preços")
        fig = px.histogram(
            df_prod, 
            x="Preço (R$)", 
            nbins=10, 
            title=f"Variação de Preço: {categoria}",
            color_discrete_sequence=['#0071e3']
        )
        fig.update_layout(template="plotly_white", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("💡 **Dica:** Preços muito baixos podem ser peças de reposição ou acessórios.")

    with c_table:
        st.subheader("🛒 Top Produtos Encontrados")
        
        # Configuração da Tabela com IMAGENS (Recurso Pro do Streamlit)
        st.dataframe(
            df_prod,
            column_config={
                "Foto": st.column_config.ImageColumn("Preview", width="small"),
                "Link": st.column_config.LinkColumn("Ver no Site"),
                "Preço (R$)": st.column_config.NumberColumn(format="R$ %.2f")
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )

else:
    st.warning("Não foi possível carregar os produtos do Mercado Livre no momento.")

# 3. CALCULADORA DE IMPORTAÇÃO RÁPIDA
st.markdown("---")
with st.expander("🧮 Calculadora Rápida de Importação (Simulação)", expanded=True):
    col_a, col_b, col_c = st.columns(3)
    
    valor_dolar = col_a.number_input("Preço no Fornecedor (US$)", value=10.0, step=1.0)
    taxa_imposto = col_b.slider("Imposto de Importação (%)", 0, 100, 60)
    margem = col_c.slider("Margem de Lucro Desejada (%)", 0, 100, 30)
    
    # Contas
    custo_brl = valor_dolar * cambio['Dolar']
    custo_com_imposto = custo_brl * (1 + (taxa_imposto/100))
    preco_venda = custo_com_imposto * (1 + (margem/100))
    
    st.markdown(f"""
    ### Resultado da Simulação:
    * Custo do Produto: **R$ {custo_brl:.2f}**
    * Custo Final (com Imposto): **R$ {custo_com_imposto:.2f}**
    * **Preço de Venda Sugerido: R$ {preco_venda:.2f}**
    """)
