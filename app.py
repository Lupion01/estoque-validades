
import streamlit as st
import pandas as pd
import json
import hashlib
import os
from datetime import datetime

# ====== CSS DE ESTILO VISUAL ======
st.markdown("""
<style>
    .fade-in {
        animation: fadeIn 0.8s ease-in-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stButton>button:hover {
        background-color: #e0f7fa;
        border: 1px solid #00ACC1;
        color: black;
    }
    .stAlert.success {
        animation: fadeSuccess 0.6s ease-in-out;
    }
    @keyframes fadeSuccess {
        0% { background-color: #d4edda; }
        50% { background-color: #c3e6cb; }
        100% { background-color: #d4edda; }
    }
</style>
""", unsafe_allow_html=True)

# ====== LOGIN COM HASH ======
usuarios = {
    "bruno": {"senha": "7c2c356cadbee68f0ff37b2e3b593559761e6a80ac295d790673bfa242993867", "tipo": "Administrador"},
    "dinho": {"senha": "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4", "tipo": "Visitante"}
}

def verificar_login(user, senha):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    if user in usuarios and usuarios[user]["senha"] == senha_hash:
        return usuarios[user]["tipo"]
    return None

if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario"] = ""
    st.session_state["perfil"] = ""

if not st.session_state["logado"]:
    st.title("Login - Controle de Estoque")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        tipo = verificar_login(u, s)
        if tipo:
            st.session_state["logado"] = True
            st.session_state["usuario"] = u
            st.session_state["perfil"] = tipo
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()

# ====== FUNÇÕES AUXILIARES ======
def carregar_validades():
    if os.path.exists("validades.json"):
        with open("validades.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_validades(validades):
    with open("validades.json", "w", encoding="utf-8") as f:
        json.dump(validades, f, indent=2)

def cor_situacao(atual, ideal, media, minima):
    if atual <= minima:
        return "Crítico"
    elif atual <= media:
        return "Abaixo da Média"
    else:
        return "Ideal"

# ====== CARREGAMENTO DE DADOS ======
df = pd.read_excel("estoque_dashboard_FINAL.xlsx")
validades = carregar_validades()

# ====== CÁLCULO DO ESTOQUE COM BASE NAS VALIDADES ======
estoques_atuais = []
for _, row in df.iterrows():
    produto = row["Produto"]
    lotes = validades.get(produto, [])
    total = sum([int(l["quantidade"]) for l in lotes])
    estoques_atuais.append(total)

df["Estoque Atual"] = estoques_atuais
df["Situação"] = df.apply(lambda row: cor_situacao(row["Estoque Atual"], row["Ideal"], row["Média"], row["Mínima"]), axis=1)

# ====== INTERFACE DE CATEGORIAS ======
categorias = ["Resumo Geral"] + df["Categoria"].unique().tolist()
abas = st.tabs(categorias)

for i, categoria in enumerate(categorias):
    with abas[i]:
        if categoria == "Resumo Geral":
            st.subheader("Produtos com Estoque Crítico ou Abaixo da Média")
            df_cat = df[df["Situação"].isin(["Crítico", "Abaixo da Média"])]
        else:
            st.subheader(f"Categoria: {categoria}")
            df_cat = df[df["Categoria"] == categoria]

        for _, row in df_cat.iterrows():
            produto = row["Produto"]
            estoque = row["Estoque Atual"]
            situacao = row["Situação"]

            st.markdown(f"### 🔹 {produto}")
            st.markdown(f"**Estoque:** {estoque} &nbsp;&nbsp;|&nbsp;&nbsp; **Situação:** <span style='background-color:{'#ff4d4f' if situacao=='Crítico' else '#ffc53d' if situacao=='Abaixo da Média' else '#52c41a'}; color:white; padding:2px 6px; border-radius:4px;'>{situacao}</span>", unsafe_allow_html=True)

            lotes = validades.get(produto, [])
            if lotes:
                st.markdown("**Lotes:**")
                for lote in lotes:
                    st.markdown(f"- {lote['quantidade']} unid — validade {lote['validade']}")
            else:
                st.info("Nenhum lote cadastrado.")

            if st.session_state["perfil"] == "Administrador":
                with st.expander("➕ Entrada"):
                    qtd = st.number_input(f"Quantidade a adicionar", min_value=1, step=1, key=f"ent_{produto}_{i}")
                    val = st.date_input(f"Validade", key=f"val_{produto}_{i}")
                    if st.button("Registrar Entrada", key=f"btnent_{produto}_{i}"):
                        val_format = val.strftime("%d/%m/%Y")
                        validades.setdefault(produto, []).append({"quantidade": qtd, "validade": val_format})
                        salvar_validades(validades)
                        st.success("Entrada registrada!")
                        st.rerun()

                with st.expander("➖ Saída"):
                    saida = st.number_input(f"Quantidade a remover", min_value=1, step=1, key=f"sa_{produto}_{i}")
                    if st.button("Registrar Saída", key=f"btnsa_{produto}_{i}"):
                        lotes_ordenados = sorted(validades.get(produto, []), key=lambda x: datetime.strptime(x['validade'], "%d/%m/%Y"))
                        restante = saida
                        novos_lotes = []
                        for lote in lotes_ordenados:
                            qtd_lote = int(lote["quantidade"])
                            if restante == 0:
                                novos_lotes.append(lote)
                            elif restante >= qtd_lote:
                                restante -= qtd_lote
                            else:
                                lote["quantidade"] = qtd_lote - restante
                                novos_lotes.append(lote)
                                restante = 0
                        if restante > 0:
                            st.error("Estoque insuficiente!")
                        else:
                            validades[produto] = novos_lotes
                            salvar_validades(validades)
                            st.success("Saída registrada!")
                            st.rerun()

# ====== LOGOUT ======
with st.sidebar:
    st.write(f"Usuário: **{st.session_state['usuario']}**")
    if st.button("🚪 Sair"):
        st.session_state["logado"] = False
        st.session_state["usuario"] = ""
        st.session_state["perfil"] = ""
        st.rerun()
