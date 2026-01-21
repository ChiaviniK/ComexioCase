import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="E-Comex Tracker", page_icon="🛍️", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f5f5f7; color: #1d1d1f; }
    h1, h2, h3 { color: #0071e3 !important; font-family: 'Helvetica Neue', sans-serif; }
    div[data-testid="stMetric"] {
        background-color: white; border-radius: 12px; padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e5e5;
    }
    /* Destaque para a área de detalhes */
    .product-card {
        background-color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES (API) ---
@st.cache_data(ttl=60)
def get_real_currency():
    url = "https://economia.awesomeapi.com.br/last/USD-BRL,CNY-BRL"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            return {
                'Dolar': float(data['USDBRL']['bid']),
                'Yuan': float(data['CNYBRL']['bid']),
                'Time': datetime.now().strftime("%H:%M")
            }
    except:
        pass
    return {'Dolar': 5.80, 'Yuan': 0.80, 'Time': 'N/A'}

@st.cache_data(ttl=300)
def get_ml_products(query):
    # Limitamos a 50 produtos para ter bastante opção
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={query}&limit=50"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            products = []
            for item in data['results']:
                # Tenta pegar imagem de alta resolução se disponível, senão pega thumbnail
                # O ID da imagem geralmente permite pegar versões maiores substituindo I por V
                img_url = item['thumbnail'].replace("-I.jpg", "-V.jpg") 
                
                products.append({
                    'ID': item['id'],
                    'Foto': item['thumbnail'], # Miniatura para a tabela
                    'Foto_Grande': img_url,    # Grande para o destaque
                    'Produto': item['title'],
                    'Preço': item['price'],
                    'Link': item['permalink']
                })
            return pd.DataFrame(products)
    except:
        pass
    return pd.DataFrame()

# --- CARGA INICIAL ---
cambio = get_real_currency()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/3d-fluency/96/box.png", width=80)
    st.title("E-Comex")
    st.markdown("---")
    categoria = st.selectbox(
        "📦 Categoria:",
        ["Xiaomi Redmi", "Drone DJI", "PlayStation 5", "iPhone 13", "Alexa Echo"]
    )
    st.info(f"Dólar: R$ {cambio['Dolar']:.2f}")

# --- MAIN ---
st.title(f"Monitor de Mercado: {categoria}")

# Busca produtos
df_prod = get_ml_products(categoria)

if not df_prod.empty:
    
    # DIVISÃO DA TELA (MESTRE-DETALHE)
    # Coluna 1 (Tabela) ocupa 60% | Coluna 2 (Detalhes) ocupa 40%
    col_tabela, col_detalhe = st.columns([1.5, 1])
    
    with col_tabela:
        st.subheader("📋 Lista de Produtos")
        st.caption("Selecione uma linha para ver a foto ampliada.")
        
        # O SEGREDINHO: on_select="rerun"
        # Isso avisa o Streamlit para rodar o código de novo quando alguém clica
        event = st.dataframe(
            df_prod[['Foto', 'Produto', 'Preço']],
            column_config={
                "Foto": st.column_config.ImageColumn("Preview", width="small"),
                "Preço": st.column_config.NumberColumn("Valor (BRL)", format="R$ %.2f"),
                "Produto": st.column_config.TextColumn("Nome do Item", width="medium")
            },
            hide_index=True,
            use_container_width=True,
            on_select="rerun",       # Habilita o clique
            selection_mode="single-row", # Só pode selecionar 1 por vez
            height=500
        )

    with col_detalhe:
        # LÓGICA DO CLIQUE
        # Verifica se alguém clicou em alguma linha
        if len(event.selection['rows']) > 0:
            idx_selecionado = event.selection['rows'][0] # Pega o índice da linha
            produto_sel = df_prod.iloc[idx_selecionado]  # Pega os dados do produto
            
            # MOSTRA OS DETALHES
            st.markdown(f"""
            <div class="product-card">
                <h3>🔍 Detalhes do Item</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.image(produto_sel['Foto_Grande'], use_container_width=True)
            
            st.markdown(f"### {produto_sel['Produto']}")
            st.metric("Preço de Mercado", f"R$ {produto_sel['Preço']:.2f}")
            
            # Simulação de Importação para este item específico
            custo_china = (produto_sel['Preço'] * 0.4) / cambio['Dolar']
            st.info(f"🇨🇳 Custo Estimado na China: **US$ {custo_china:.2f}**")
            
            st.link_button("🔗 Ver no Mercado Livre", produto_sel['Link'])
            
        else:
            # Estado Inicial (Ninguém clicou ainda)
            st.info("👈 Clique em um produto na tabela ao lado para ver a foto ampliada e análise de custos.")
            st.image("https://img.icons8.com/clouds/200/search.png", width=200)

else:
    st.error("Erro ao carregar produtos. Tente outra categoria.")
