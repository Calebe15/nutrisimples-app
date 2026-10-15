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
if "NVIDIA_API_KEY" in st.secrets:
    api_key = st.secrets["NVIDIA_API_KEY"].strip()
else:
    api_key = None

client = None
if api_key:
    client = OpenAI(
        base_url="https://nvidia.com",
        api_key=api_key
    )

# --- DICIONÁRIO DE ADITIVOS E CONSERVANTES ---
DICIONARIO_ADITIVOS = {
    "aspartame": {"nome": "Aspartame (INS 951)", "cat": "Edulcorante Artificial", "risco": "🚨 Evitar", "desc": "Adoçante artificial muito debatido. Pode causar dores de cabeça em pessoas sensíveis e deve ser totalmente evitado por portadores de fenilcetonúria."},
    "sucralose": {"nome": "Sucralose (INS 955)", "cat": "Edulcorante", "risco": "⚠️ Atenção", "desc": "Derivado do açúcar, mas artificial. Seguro em doses normais, mas estudos sugerem cautela com o aquecimento e impacto na flora intestinal."},
    "acessulfame": {"nome": "Acessulfame de Potássio (INS 950)", "cat": "Edulcorante Artificial", "risco": "⚠️ Atenção", "desc": "Adoçante sintético frequentemente combinado com o aspartame. Consumir com moderação."},
    "ciclamato": {"nome": "Ciclamato de Sódio (INS 952)", "cat": "Edulcorante Artificial", "risco": "🚨 Evitar", "desc": "Banido em alguns países devido a estudos antigos sobre toxicidade. Uso controlado no Brasil."},
    "sacarina": {"nome": "Sacarina Sódica (INS 954)", "cat": "Edulcorante Artificial", "risco": "⚠️ Atenção", "desc": "Um dos adoçantes artificiais mais antigos. Deixa sabor residual amargo e deve ser consumido com moderação."},
    "tartrazina": {"nome": "Corante Tartrazina (INS 102)", "cat": "Corante Artificial", "risco": "🚨 Evitar", "desc": "Corante amarelo associado a reações alérgicas, crises de asma e hiperatividade em crianças. Exige aviso no róvulo por lei."},
    "crepúsculo": {"nome": "Amarelo Crepúsculo (INS 110)", "cat": "Corante Artificial", "risco": "🚨 Evitar", "desc": "Corante artificial que pode desencadear reações alérgicas e está sob constante vigilância de segurança alimentar."},
    "caramelo iv": {"nome": "Corante Caramelo IV (INS 150d)", "cat": "Corante", "risco": "🚨 Evitar", "desc": "Processado com amônia e sulfitos. Contém o composto 4-MEI, que é classificado como possivelmente carcinogênico em altas doses."},
    "cochonilha": {"nome": "Corante Carmim de Cochonilha (INS 120)", "cat": "Corante Natural", "risco": "⚠️ Atenção", "desc": "Extraído de um insecto. Embora natural, é um forte alérgeno para pessoas sensíveis e inadequado para veganos."},
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
st.markdown("Cole a lista de ingredientes ou use a câmera do seu celular para entender o que você está comendo.")

aba_manual, aba_camera = st.tabs(["✍️ Digitar Manualmente", "📸 Escanear por Foto/Câmera"])

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
    ingredientes_manuais = st.text_area("Lista de Ingredientes:", placeholder="Ex: açúcar, farinha de trigo...", key="txt_ingredientes")
    
    col1, col2, col3 = st.columns(3)
    with col1: acucar_manual = st.number_input("Açúcares Totais (g)", min_value=0.0, step=0.1, value=0.0, key="num_acucar")
    with col2: gordura_manual = st.number_input("Gordura Saturada (g)", min_value=0.0, step=0.1, value=0.0, key="num_gordura")
    with col3: sodio_manual = st.number_input("Sódio (mg)", min_value=0.0, step=1.0, value=0.0, key="num_sodio")
        
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
        st.warning("⚠️ Chave de API da NVIDIA não configurada nos Secrets.")
    
    arquivo_foto = st.camera_input("Tire uma foto nítida do rótulo")
    
    if arquivo_foto is not None and client:
        if st.button("🤖 Ler Rótulo com Nemotron-3.5", type="primary"):
            with st.spinner("A IA da NVIDIA está processando a imagem..."):
                try:
                    bytes_foto = arquivo_foto.getvalue()
                    base64_image = base64.b64encode(bytes_foto).decode('utf-8')
                    data_url = f"data:image/jpeg;base64,{base64_image}"
                    
                    prompt = "Retorne os dados textualmente com os prefixos exatamente assim: INGREDIENTES: lista de ingredientes. ACUCAR: valor. GORDURA: valor. SODIO: valor."
                    
                    completion = client.chat.completions.create(
                        model="nvidia/nemotron-3.5-super-vl-120b-a12b",
                        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": data_url}}]}],
                        temperature=0.1,
                        max_tokens=1024
                    )
                    
                    resposta_texto = completion.choices.message.content
                    
                    ingredientes_busca = re.search(r"INGREDIENTES:\s*(.*)", resposta_texto, re.IGNORECASE)
                    acucar_busca = re.search(r"ACUCAR:\s*([\d.,\s]+)", resposta_texto, re.IGNORECASE)
                    gordura_busca = re.search(r"GORDURA:\s*([\d.,\s]+)", resposta_texto, re.IGNORECASE)
                    sodio_busca = re.search(r"SODIO:\s*([\d.,\s]+)", resposta_texto, re.IGNORECASE)
                    
                    st.session_state.lista_ingredientes = ingredientes_busca.group(1).strip() if ingredientes_busca else ""
                    
                    def extrair_numero(match_obj):
                        if not match_obj: return 0.0
                        numeros = re.findall(r"\d+\.?\d*", match_obj.group(1).replace(",", "."))
                        return float(numeros[0]) if numeros else 0.0

                    st.session_state.acucar = extrair_numero(acucar_busca)
                    st.session_state.gordura = extrair_numero(gordura_busca)
                    st.session_state.sodio = extrair_numero(sodio_busca)
                    st.session_state.disparar_analise = True
                    st.success("✅ Processamento concluído!")
                except Exception as e:
                    st.error(f"Erro no processamento da imagem: {e}")

        if st.session_state.lista_ingredientes:
            st.info("🔍 Dados capturados:")
