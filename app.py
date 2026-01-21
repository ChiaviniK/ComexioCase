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
    .product-card {
        background-color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- DADOS DE BACKUP (CASO A API FALHE) ---
def get_mock_products(categoria):
    """Retorna dados simulados para a aula não parar."""
    # Links de imagens estáticas para exemplo
    img_padrao = "https://http2.mlstatic.com/D_NQ_NP_796792-MLA46915684000_072021-O.webp"
    
    mock_db = {
        "Xiaomi Redmi": [
            {"ID": "1", "Foto": img_padrao, "Foto_Grande": img_padrao, "Produto": "Xiaomi Redmi Note 13 256gb (Simulado)", "Preço": 1200.00, "Link": "#"},
            {"ID": "2", "Foto": img_padrao, "Foto_Grande": img_padrao, "Produto": "Xiaomi Redmi 12C 128gb (Simulado)", "Preço": 850.00, "Link": "#"},
            {"ID": "3", "Foto": img_padrao, "Foto_Grande": img_padrao, "Produto": "Xiaomi Pocophone X6 Pro (Simulado)", "Preço": 2100.00, "Link": "#"},
        ],
        "Drone DJI": [
            {"ID": "1", "Foto": img_padrao, "Foto_Grande": img_padrao, "Produto": "Drone DJI Mini 3 Pro (Simulado)", "Preço": 5500.00, "Link": "#"},
            {"ID": "2", "Foto": img_padrao, "Foto_Grande": img_padrao, "Produto": "Drone DJI Mavic Air 2 (Simulado)", "Preço": 7200.00, "Link": "#"},
        ]
    }
    
    lista = mock_db.get(categoria, mock_db["Xiaomi Redmi"]) # Padrão Xiaomi se não achar
    return pd.DataFrame(lista)

# --- FUNÇÕES (API) ---
@st.cache_data(ttl=60)
def get_real_currency():
    # Tenta AwesomeAPI com timeout curto
    url = "https://economia.awesomeapi.com.br/last/USD-BRL,CNY-BRL"
    try:
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            data = r.json()
            return {
                'Dolar': float(data['USDBRL']['bid']),
                'Yuan': float(data['CNYBRL']['bid']),
                'Time': datetime.now().strftime("%H:%M")
            }
    except:
        pass
    # Backup se a API de cambio falhar
    return {'Dolar': 5.80, 'Yuan': 0.80, 'Time': 'Offline'}

@st.cache_data(ttl=300)
def get_ml_products(query):
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={query}&limit=50"
    
    # Headers para fingir que somos um navegador (evita bloqueio 403)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=5)
        
        if r.status_code == 200:
            data = r.json()
            products = []
            if 'results' not in data: return get_mock_products(query) # Se vier vazio, usa Mock
            
            for item in data['results']:
                # Tenta pegar imagem HD
                img_url = item.get('thumbnail', '').replace("-I.jpg", "-V.jpg")
                
                products.append({
                    'ID': item.get('id'),
                    'Foto': item.get('thumbnail'),
                    'Foto_Grande': img_url,
                    'Produto': item.get('title'),
                    'Preço': item.get('price'),
                    'Link': item.get('permalink')
                })
            
            if len(products) == 0: return get_mock_products(query)
            return pd.DataFrame(products)
            
        else:
            # Se der erro 403/429/500, usa Mock
            return get_mock_products(query)
            
    except Exception as e:
        print(f"Erro API: {e}")
        return get_mock_products(query)

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
    st.info(f"Dólar Ref: R$ {cambio['Dolar']:.2f}")

# --- MAIN ---
st.title(f"Monitor de Mercado: {categoria}")

# Busca produtos (Com Blindagem Mock)
df_prod = get_ml_products(categoria)

if not df_prod.empty:
    
    # Layout Mestre-Detalhe
    col_tabela, col_detalhe = st.columns([1.5, 1])
    
    with col_tabela:
        st.subheader("📋 Lista de Produtos")
        
        event = st.dataframe(
            df_prod[['Foto', 'Produto', 'Preço']],
            column_config={
                "Foto": st.column_config.ImageColumn("Preview", width="small"),
                "Preço": st.column_config.NumberColumn("Valor (BRL)", format="R$ %.2f"),
                "Produto": st.column_config.TextColumn("Nome do Item", width="medium")
            },
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            height=500
        )

    with col_detalhe:
        # Verifica clique
        if len(event.selection['rows']) > 0:
            idx_selecionado = event.selection['rows'][0]
            produto_sel = df_prod.iloc[idx_selecionado]
            
            # Card de Detalhes
            st.markdown(f"""
            <div class="product-card">
                <h3>🔍 Análise do Item</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Imagem Grande
            st.image(produto_sel['Foto_Grande'], use_container_width=True)
            
            st.markdown(f"### {produto_sel['Produto']}")
            st.metric("Preço de Venda (BR)", f"R$ {produto_sel['Preço']:.2f}")
            
            # Conta de Importação
            custo_china = (produto_sel['Preço'] * 0.4) / cambio['Dolar']
            st.success(f"🇨🇳 Custo Estimado China: **US$ {custo_china:.2f}**")
            
            st.link_button("🔗 Ver no Mercado Livre", produto_sel['Link'])
            
        else:
            st.info("👈 Clique na tabela para analisar um produto.")
            st.caption("Aguardando seleção...")

else:
    # Se até o Mock falhar (impossível, mas...)
    st.error("Erro crítico. Reinicie a aplicação.")
