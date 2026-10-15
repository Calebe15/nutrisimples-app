import streamlit as st
import pandas as pd
import re
from PIL import Image
import base64
from openai import OpenAI

st.set_page_config(page_title="NutriSimples - Intérprete de Rótulos", page_icon="🌱", layout="wide")

api_key = st.secrets["NVIDIA_API_KEY"].strip() if "NVIDIA_API_KEY" in st.secrets else None
client = OpenAI(base_url="https://nvidia.com", api_key=api_key) if api_key else None

DICIONARIO_ADITIVOS = {
    "aspartame": {"nome": "Aspartame (INS 951)", "cat": "Edulcorante Artificial", "risco": "🚨 Evitar", "desc": "Pode causar dores de cabeça e deve ser evitado por fenilcetonúricos."},
    "sucralose": {"nome": "Sucralose (INS 955)", "cat": "Edulcorante", "risco": "⚠️ Atenção", "desc": "Derivado do açúcar artificial. Cautela com o aquecimento e flora intestinal."},
    "acessulfame": {"nome": "Acessulfame K (INS 950)", "cat": "Edulcorante Artificial", "risco": "⚠️ Atenção", "desc": "Adoçante sintético. Consumir com moderação."},
    "ciclamato": {"nome": "Ciclamato de Sódio (INS 952)", "cat": "Edulcorante Artificial", "risco": "🚨 Evitar", "desc": "Banido em alguns países. Uso controlado no Brasil."},
    "sacarina": {"nome": "Sacarina Sódica (INS 954)", "cat": "Edulcorante Artificial", "risco": "⚠️ Atenção", "desc": "Deixa sabor residual amargo. Consumir com moderação."},
    "tartrazina": {"nome": "Tartrazina (INS 102)", "cat": "Corante Artificial", "risco": "🚨 Evitar", "desc": "Associado a reações alérgicas e hiperatividade em crianças."},
    "crepúsculo": {"nome": "Amarelo Crepúsculo (INS 110)", "cat": "Corante Artificial", "risco": "🚨 Evitar", "desc": "Sob constante vigilância de segurança alimentar."},
    "caramelo iv": {"nome": "Corante Caramelo IV (INS 150d)", "cat": "Corante", "risco": "🚨 Evitar", "desc": "Contém 4-MEI, possivelmente carcinogênico em altas doses."},
    "cochonilha": {"nome": "Corante Carmim (INS 120)", "cat": "Corante Natural", "risco": "⚠️ Atenção", "desc": "Extraído de inseto. Forte alérgeno e inadequado para veganos."},
    "nitrito de sódio": {"nome": "Nitrito de Sódio (INS 250)", "cat": "Conservante", "risco": "🚨 Evitar", "desc": "Usado em embutidos. Pode formar nitrosaminas no estômago."},
    "nitrato de sódio": {"nome": "Nitrato de Sódio (INS 251)", "cat": "Conservante", "risco": "🚨 Evitar", "desc": "Utilizado para conservar carnes processadas e manter a cor."},
    "benzoato de sódio": {"nome": "Benzoato de Sódio (INS 211)", "cat": "Conservante", "risco": "⚠️ Atenção", "desc": "Pode reagir com a Vitamina C gerando benzeno, substância tóxica."},
    "sorbato de potássio": {"nome": "Sorbato de Potássio (INS 202)", "cat": "Conservante", "risco": "✅ Seguro", "desc": "Considerado um dos conservantes mais seguros pela ciência."},
    "glutamato monossódico": {"nome": "Glutamato (INS 621)", "cat": "Realçador de Sabor", "risco": "⚠️ Atenção", "desc": "Pode causar dores de cabeça ou fome excessiva em algumas pessoas."},
    "bha": {"nome": "BHA (INS 320)", "cat": "Antioxidante Sintético", "risco": "🚨 Evitar", "desc": "Potencial interferente endócrino pela comunidade científica."},
    "bht": {"nome": "BHT (INS 321)", "cat": "Antioxidante Sintético", "risco": "🚨 Evitar", "desc": "Usado para estender a validade de óleos. Evitar o excesso."},
    "carboximetilcelulose": {"nome": "CMC (INS 466)", "cat": "Espessante", "risco": "✅ Seguro", "desc": "Derivado de fibras vegetais, serve para dar textura."},
    "goma xantana": {"nome": "Goma Xantana (INS 415)", "cat": "Espessante", "risco": "✅ Seguro", "desc": "Totalmente segura, ajuda na textura de molhos e pães."},
    "goma guar": {"nome": "Goma Guar (INS 412)", "cat": "Espessante", "risco": "✅ Seguro", "desc": "Extraída de leguminosa. Atua também como fibra alimentar."},
    "carragena": {"nome": "Carragena (INS 407)", "cat": "Espessante", "risco": "⚠️ Atenção", "desc": "Alguns estudos associam o excesso a inflamações intestinais."}
}

st.title("🌱 NutriSimples - Intérprete de Rótulos")
aba_manual, aba_camera = st.tabs(["✍️ Digitar Manualmente", "📸 Escanear por Foto/Câmera"])

if "lista_ingredientes" not in st.session_state: st.session_state.lista_ingredientes = ""
if "acucar" not in st.session_state: st.session_state.acucar = 0.0
if "gordura" not in st.session_state: st.session_state.gordura = 0.0
if "sodio" not in st.session_state: st.session_state.sodio = 0.0
if "disparar_analise" not in st.session_state: st.session_state.disparar_analise = False

with aba_manual:
    st.subheader("🔍 Inserir Dados do Produto")
    ingredientes_manuais = st.text_area("Lista de Ingredientes:", placeholder="Ex: açúcar, farinha de trigo...")
    col1, col2, col3 = st.columns(3)
    with col1: acucar_manual = st.number_input("Açúcares Totais (g)", min_value=0.0, value=0.0, key="m1")
    with col2: gordura_manual = st.number_input("Gordura Saturada (g)", min_value=0.0, value=0.0, key="m2")
    with col3: sodio_manual = st.number_input("Sódio (mg)", min_value=0.0, value=0.0, key="m3")
    if st.button("Traduzir Rótulo", type="primary", key="b1"):
        st.session_state.lista_ingredientes = ingredientes_manuais
        st.session_state.acucar, st.session_state.gordura, st.session_state.sodio = acucar_manual, gordura_manual, sodio_manual
        st.session_state.disparar_analise = True

with aba_camera:
    st.subheader("📷 Escaneamento Inteligente de Rótulos")
    if not client: st.warning("⚠️ Chave de API da NVIDIA não configurada nos Secrets.")
    arquivo_foto = st.camera_input("Tire uma foto nítida do rótulo")
    if arquivo_foto is not None and client:
        if st.button("🤖 Ler Rótulo com Nemotron-3.5", type="primary"):
            with st.spinner("Processando imagem com a IA da NVIDIA..."):
                base64_image = base64.b64encode(arquivo_foto.getvalue()).decode('utf-8')
                prompt = "Analise o rótulo. Retorne estritamente neste formato de texto:\nINGREDIENTES: lista\nACUCAR: numero\nGORDURA: numero\nSODIO: numero"
                completion = client.chat.completions.create(
                    model="nvidia/nemotron-3.5-super-vl-120b-a12b",
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                    temperature=0.1, max_tokens=1024, extra_body={"chat_template_kwargs": {"enable_thinking": False}}
                )
                rt = completion.choices.message.content
                ib = re.search(r"INGREDIENTES:\s*(.*)", rt, re.IGNORECASE)
                ab = re.search(r"ACUCAR:\s*([\d.,\s]+)", rt, re.IGNORECASE)
                gb = re.search(r"GORDURA:\s*([\d.,\s]+)", rt, re.IGNORECASE)
                sb = re.search(r"SODIO:\s*([\d.,\s]+)", rt, re.IGNORECASE)
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

if st.session_state.disparar_analise:
    st.markdown("---")
    st.header("📊 Interpretação Descomplicada")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="Açúcar", value=f"{st.session_state.acucar} g")
        st.error("🚨 ALTO TEOR!") if st.session_state.acucar >= 15.0 else st.success("✅ Controlado.")
    with c2:
        st.metric(label="Gordura", value=f"{st.session_state.gordura} g")
        st.error("🚨 ALTO TEOR!") if st.session_state.gordura >= 6.0 else st.success("✅ Seguro.")
    with c3:
        st.metric(label="Sódio", value=f"{st.session_state.sodio} mg")
        st.error("🚨 ALTO TEOR!") if st.session_state.sodio >= 600.0 else st.success("✅ Aceitável.")
    st.subheader("🕵️‍♂️ Análise dos Ingredientes Ocultos")
    texto_lower = st.session_state.lista_ingredientes.lower()
    encontrados = [info for chave, info in DICIONARIO_ADITIVOS.items() if chave in texto_lower]
    if encontrados:
        for aditivo in encontrados:
            with st.expander(f"{aditivo['risco']} - {aditivo['nome']} ({aditivo['cat']})"): st.write(aditivo['desc'])
    else: st.success("🎉 Nenhum aditivo crítico detectado!")
