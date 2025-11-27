import streamlit as st
import requests
import pandas as pd

st.title("🍎 Projeto Fitness — Dashboard Completo")

FUNCTION_URL = st.secrets.get("FUNCTION_BASE_URL", "https://SEU_FUNCTION.azurewebsites.net/api/HttpTrigger")

aba = st.sidebar.radio("Menu", ["Ingestão", "TMB", "Relatório"])

if aba == "Ingestão":
    st.header("Registro de Ingestão")
    alimento = st.text_input("Alimento")
    qt = st.number_input("Quantidade (g)", 0)
    if st.button("Registrar"):
        r = requests.get(FUNCTION_URL, params={
            "action": "calc",
            "alimento": alimento,
            "quantidade": qt
        })
        st.json(r.json())

if aba == "TMB":
    st.header("Cálculo Harris-Benedict")
    sexo = st.selectbox("Sexo", ["Masculino", "Feminino"])
    peso = st.number_input("Peso (kg)", 1)
    altura = st.number_input("Altura (cm)", 50)
    idade = st.number_input("Idade", 1)
    atividade = st.selectbox("Atividade", ["sedentario", "leve", "moderado", "intenso", "muito_intenso"])
    if st.button("Calcular TMB"):
        r = requests.post(FUNCTION_URL + "?action=tmb", json={
            "sexo": sexo,
            "peso": peso,
            "altura": altura,
            "idade": idade,
            "atividade": atividade
        })
        st.json(r.json())

if aba == "Relatório":
    st.header("Relatório Diário")
    r = requests.get(FUNCTION_URL, params={"action": "relatorio"})
    resp = r.json()
    st.json(resp)

    if "calorias_consumidas" in resp:
        st.bar_chart(pd.DataFrame({
            "Calorias Consumidas": [resp["calorias_consumidas"]],
            "GET": [resp["tmb_info"]["get"]]
        }))
