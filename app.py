import streamlit as st
import pandas as pd
import re
from PIL import Image
import json
import base64
import io
from openai import OpenAI

# Configuração da página do Streamlit
st.set_page_config(
    page_title="NutriSimples - Intérprete de Rótulos",
    page_icon="🌱",
    layout="wide"
)

# --- CONFIGURAÇÃO DA IA (NVIDIA NEMOTRON) ---
# O sistema puxa a chave que você configurou em TOML no Secrets
if "NVIDIA_API_KEY" in st.secrets:
    api_key = st.secrets["NVIDIA_API_KEY"]
else:
    api_key = None

# Inicializa o cliente apontando para o servidor da NVIDIA
client = None
if api_key:
    client = OpenAI(
        base_url="https://nvidia.com",
        api_key=api_key
    )

# --- DICIONÁRIO EXPANDIDO DE ADITIVOS E CONSERVANTES ---
DICIONARIO_ADITIVOS = {
    "aspartame": {"nome": "Aspartame (INS 951)", "cat": "Edulcorante Artificial", "risco": "🚨 Evitar", "desc": "Adoçante artificial muito debatido. Pode causar dores de cabeça em pessoas sensíveis e deve ser totalmente evitado por portadores de fenilcetonúria."},
    "sucralose": {"nome": "Sucralose (INS 955)", "cat": "Edulcorante", "risco": "⚠️ Atenção", "desc": "Derivado do açúcar, mas artificial. Seguro em doses normais, mas estudos sugerem cautela com o aquecimento e impacto na flora intestinal."},
    "acessulfame": {"nome": "Acessulfame de Potássio (INS 950)", "cat": "Edulcorante Artificial", "risco": "⚠️ Atenção", "desc": "Adoçante sintético frequentemente combinado com o aspartame. Consumir com moderação."},
    "ciclamato": {"nome": "Ciclamato de Sódio (INS 952)", "cat": "Edulcorante Artificial", "risco": "🚨 Evitar", "desc": "Banido em alguns países devido a estudos antigos sobre toxicidade. Uso controlado no Brasil."},
    "sacarina": {"nome": "Sacarina Sódica (INS 954)", "cat": "Edulcorante Artificial", "risco": "⚠️ Atenção", "desc": "Um dos adoçantes artificiais mais antigos. Deixa sabor residual amargo e deve ser consumido com moderação."},
    "tartrazina": {"nome": "Corante Tartrazina (INS 102)", "cat": "Corante Artificial", "risco": "🚨 Evitar", "desc": "Corante amarelo associado a reações alérgicas, crises de asma e hiperatividade em crianças. Exige aviso no róvulo por lei."},
    "crepúsculo": {"nome": "Amarelo Crepúsculo (INS 110)", "cat": "Corante Artificial", "risco": "🚨 Evitar", "desc": "Corante artificial que pode desencadear reações alérgicas e está sob constante vigilância de segurança alimentar."},
    "caramelo iv": {"nome": "Corante Caramelo IV (INS 150d)", "cat": "Corante", "risco": "🚨 Evitar", "desc": "Processado com amônia e sulfitos. Contém o composto 4-MEI, que é classificado como possivelmente carcinogênico em altas doses."},
    "cochonilha": {"nome": "Corante Carmim de Cochonilha (INS 120)", "cat": "Corante Natural", "risco": "⚠️ Atenção", "desc": "Extraído de um inseto. Embora natural, é um forte alérgeno para pessoas sensíveis e inadequado para veganos."},
    "nitrito de sódio": {"nome": "Nitrito de Sódio (INS 250)", "cat": "Conservante", "risco": "🚨 Evitar", "desc": "Usado em embutidos (salsicha, presunto). No estômago, pode formar nitrosaminas, compostos associados ao aumento do risco de câncer colorretal."},
    "nitrato de sódio": {"nome": "Nitrato de Sódio (INS 251)", "cat": "Conservante", "risco": "🚨 Evitar", "desc": "Semelhante ao nitrito, amplamente utilizado para conservar carnes processadas e manter a cor avermelhada."},
    "benzoato de sódio": {"nome": "Benzoato de Sódio (INS 211)", "cat": "Conservante", "risco": "⚠️ Atenção", "desc": "Usado em refrigerantes e sucos. Pode reagir com a Vitamina C gerando benzeno, substância tóxica."},
    "sorbato de potássio": {"nome": "Sorbato de Potássio (INS 202)", "cat": "Conservante", "risco": "✅ Seguro", "desc": "Considerado um dos conservantes mais seguros pela ciência, bloqueia o crescimento de fungos e leveduras com baixa toxicidade."},
    "glutamato monossódico": {"nome": "Glutamato Monossódico (INS 621)", "cat": "Realçador de Sabor", "risco": "⚠️ Atenção", "desc": "Estimula receptores nas papilas gustativas para deixar o alimento super saboroso. Pode causar dores de cabeça ou fome excessiva em algumas pessoas."},
    "bha": {"nome": "BHA - Butil-hidroxianisol (INS 320)", "cat": "Antioxidante Sintético", "risco": "🚨 Evitar", "desc": "Evita que gorduras fiquem rançosas, mas é considerado um potencial interferente endócrino pela comunidade científica."},
    "bht": {"nome": "BHT - Butil-hidróxitolueno (INS 321)", "cat": "Antioxidante Sintético", "risco": "🚨 Evitar", "desc": "Muito parecido com o BHA, usado para estender a validade de óleos e cereais. Recomenda-se evitar o excesso."},
    "carboximetilcelulose": {"nome": "Carboximetilcelulose / CMC (INS 466)", "cat": "Espessante", "risco": "✅ Seguro", "desc": "Derivado de fibras vegetais, serve para dar textura e corpo. Seguro em consumo normal."},
    "goma xantana": {"nome": "Goma Xantana (INS 415)", "cat": "Espessante/Estabilizante", "risco": "✅ Seguro", "desc": "Fibra solúvel natural obtida por fermentação. Totalmente segura, ajuda na textura de molhos e pães sem glúten."},
    "goma guar": {"nome": "Goma Guar (INS 412)", "cat": "Espessante", "risco": "✅ Seguro", "desc": "Extraída de uma planta leguminosa. Segura e atua também como fibra alimentar no organismo."},
    "carragena": {"nome": "Carragena (INS 407)", "cat": "Espessante/Estabilizante", "risco": "⚠️ Atenção", "desc": "Extraída de algas marinhas, muito comum em laticínios. Alguns estudos associam o excesso a inflamações intestinais leves."}
}

st.title("🌱 NutriSimples - Intérprete de Rótulos")
st.markdown("Cole a lista de ingredientes e os dados principais ou use a câmera do seu celular para entender o que você está comendo de forma descomplicada.")

aba_manual, aba_camera = st.tabs(["✍️ Digitar Manualmente", "📸 Escanear por Foto/Câmera"])

# Sistema de persistência de estados do Streamlit
if "lista_ingredientes" not in st.session_state:
    st.session_state.lista_ingredientes = ""
if "acucar" not in st.session_state:
    st.session_state.acucar = 0.0
if "gordura" not in st.session_state:
    st.session_state.gordura = 0.0
if "sodio" not in st.session_state:
    st.session_state.sodio = 0.0
if "disparar_analise" not in st.session_state:
    st.session_state.disparar_analise = False

# --- ABA 1: DIGITAÇÃO MANUAL ---
with aba_manual:
    st.subheader("🔍 Inserir Dados do Produto")
    ingredientes_manuais = st.text_area(
        "Lista de Ingredientes (Separe os termos por vírgula):",
        placeholder="Ex: açúcar, farinha de trigo, óleo de palma, glutamato monossódico, tartrazina...",
        key="txt_ingredientes"
    )
    
    st.markdown("**Tabela Nutricional (Valores por 100g ou 100ml):**")
    col1, col2, col3 = st.columns(3)
    with col1:
        acucar_manual = st.number_input("Açúcares Totais (g)", min_value=0.0, step=0.1, value=0.0, key="num_acucar")
    with col2:
        gordura_manual = st.number_input("Gordura Saturada (g)", min_value=0.0, step=0.1, value=0.0, key="num_gordura")
    with col3:
        sodio_manual = st.number_input("Sódio (mg)", min_value=0.0, step=1.0, value=0.0, key="num_sodio")
        
    if st.button("Traduzir Rótulo", type="primary", key="btn_manual"):
        st.session_state.lista_ingredientes = ingredientes_manuais
        st.session_state.acucar = acucar_manual
        st.session_state.gordura = gordura_manual
        st.session_state.sodio = sodio_manual
        st.session_state.disparar_analise = True

# --- ABA 2: ESCANEAMENTO POR CÂMERA (IA DA NVIDIA) ---
with aba_camera:
    st.subheader("📷 Escaneamento Inteligente de Rótulos")
    
    if not client:
        st.warning("⚠️ Chave de API da NVIDIA não configurada. Cadastre a `NVIDIA_API_KEY` nos Secrets para ativar a câmera.")
    
    arquivo_foto = st.camera_input("Tire uma foto nítida da tabela nutricional ou ingredientes")
    
    if arquivo_foto is not None and client:
        if st.button("🤖 Ler Rótulo com Nemotron-3.5", type="primary"):
            with st.spinner("A Super IA da NVIDIA está processando a imagem..."):
                try:
                    # Lê os bytes e converte para string em Base64 para enviar na URL do payload
                    bytes_foto = arquivo_foto.getvalue()
                    base64_image = base64.b64encode(bytes_foto).decode('utf-8')
                    data_url = f"data:image/jpeg;base64,{base64_image}"
                    
                    # Prompt estruturado para forçar retorno estrito em JSON
                    prompt = """
                    Analise a imagem deste rótulo. Extraia os dados solicitados e responda UNICAMENTE com um objeto JSON válido, sem formatações markdown extras (sem as aspas de bloco ```json).
                    Se não encontrar um nutriente, retorne 0.0 para ele.

                    {
                        "ingredientes": "lista de ingredientes por extenso separados por vírgula",
                        "acucares_totais_g": valor_numérico,
                        "gordura_saturada_g": valor_numérico,
                        "sodio_mg": valor_numérico
                    }
                    """
                    
                    # Estrutura de chamada oficial baseada no modelo Nemotron Vision da NVIDIA
                    completion = client.chat.completions.create(
                        model="nvidia/nemotron-3.5-super-vl-120b-a12b",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": data_url}}
                                ]
                            }
                        ],
                        temperature=0.2,
                        max_tokens=1024
                    )
                    
