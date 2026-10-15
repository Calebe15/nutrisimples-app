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
api_key = st.secrets["NVIDIA_API_KEY"].strip() if "NVIDIA_API_KEY" in st.secrets else None

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
st.markdown("Cole a lista de ingredientes ou use a câmera do seu celular para entender o que você está comendo.")

aba_manual, aba_camera = st.tabs(["✍️ Digitar Manualmente", "📸 Escanear por Foto/Câmera"])

if "lista_ingredientes" not in st.session_state: st.session_state.lista_ingredientes = ""
if "acucar" not in st.session_state: st.session_state.acucar = 0.0
if "gordura" not in st.session_state: st.session_state.gordura = 0.0
if "sodio" not in st.session_state: st.session_state.sodio = 0.0
if "disparar_analise" not in st.session_state: st.session_state.disparar_analise = False

# --- ABA 1: DIGITAÇÃO MANUAL ---
with aba_manual:
    st.subheader("🔍 Inserir Dados do Produto")
    ingredientes_manuais = st.text_area("Lista de Ingredientes:", placeholder="Ex: açúcar, farinha de trigo...", key="txt_ingredientes")
    
    col1, col2, col3 = st.columns(3)
    with col1: acucar_manual = st.number_input("Açúcares Totais (g)", min_value=0.0, value=0.0, key="num_acucar")
    with col2: gordura_manual = st.number_input("Gordura Saturada (g)", min_value=0.0, value=0.0, key="num_gordura")
    with col3: sodio_manual = st.number_input("Sódio (mg)", min_value=0.0, value=0.0, key="num_sodio")
        
    if st.button("Traduzir Rótulo", type="primary", key="btn_manual"):
        st.session_state.lista_ingredientes = ingredientes_manuais
        st.session_state.acucar = acucar_manual
        st.session_state.gordura = gordura_manual
        st.session_state.sodio = sodio_manual
        st.session_state.disparar_analise = True

# --- ABA 2: ESCANEAMENTO POR CÂMERA (IA DA NVIDIA BLINDADA) ---
with aba_camera:
    st.subheader("📷 Escaneamento Inteligente de Rótulos")
    if not client:
        st.warning("⚠️ Chave de API da NVIDIA não configurada nos Secrets.")
    
    arquivo_foto = st.camera_input("Tire uma foto nítida do rótulo")
    
    if arquivo_foto is not None and client:
        if st.button("🤖 Ler Rótulo com Nemotron-3.5", type="primary"):
            with st.spinner("A IA da NVIDIA está processando a imagem..."):
                bytes_foto = arquivo_foto.getvalue()
                base64_image = base64.b64encode(bytes_foto).decode('utf-8')
                
                prompt = "Localize a lista de ingredientes e os valores por 100g. Retorne exatamente assim:\nINGREDIENTES: lista\nACUCAR: numero\nGORDURA: numero\nSODIO: numero"
                
                completion = client.chat.completions.create(
                    model="nvidia/nemotron-3.5-super-vl-120b-a12b",
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                    temperature=0.1,
                    max_tokens=1024
                )
                
                resposta_texto = completion.choices.message.content
                
                ib = re.search(r"INGREDIENTES:\s*(.*)", resposta_texto, re.IGNORECASE)
                ab = re.search(r"ACUCAR:\s*([\d.,\s]+)", resposta_texto, re.IGNORECASE)
                gb = re.search(r"GORDURA:\s*([\d.,\s]+)", resposta_texto, re.IGNORECASE)
                sb = re.search(r"SODIO:\s*([\d.,\s]+)", resposta_texto, re.IGNORECASE)
                
                st.session_state.lista_ingredientes = ib.group(1).strip() if ib else "Não detectado"
                
                num_ac = re.findall(r"\d+\.?\d*", ab.group(1).replace(",", ".")) if ab else []
                num_go = re.findall(r"\d+\.?\d*", gb.group(1).replace(",", ".")) if gb else []
                num_so = re.findall(r"\d+\.?\d*", sb.group(1).replace(",", ".")) if sb else []
                
                st.session_state.acucar = float(num_ac[0]) if num_ac else 0.0
                st.session_state.gordura = float(num_go[0]) if num_go else 0.0
                st.session_state.sodio = float(num_so[0]) if num_so else 0.0
                st.session_state.disparar_analise = True
                st.success("✅ Processamento concluído!")

        if st.session_state.lista_ingredientes:
            st.info("🔍 Dados capturados:")
            st.code(f"Ingredientes: {st.session_state.lista_ingredientes}\nAçúcares: {st.session_state.acucar}g | Gordura: {st.session_state.gordura}g | Sódio: {st.session_state.sodio}mg")

# --- MOTOR DE INTERPRETAÇÃO ---
if st.session_state.disparar_analise:
    st.markdown("---")
    st.header("📊 Interpretação Descomplicada")
    
    c1, c2, c3 = st.columns(3)
    with c1:
