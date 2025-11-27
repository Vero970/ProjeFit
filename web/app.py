import streamlit as st
import requests
import os
import pandas as pd

st.set_page_config(page_title="CaloriFit", page_icon="🔥", layout="wide")
st.title("🔥 CaloriFit — Análise Completa")

FUNCTION = st.secrets.get("FUNCTION_BASE_URL", os.getenv("FUNCTION_BASE_URL", ""))

if not FUNCTION:
    st.error("Defina FUNCTION_BASE_URL como secret do Streamlit ou variável de ambiente.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📥 Ingestão de Alimentos", "🔥 Harris-Benedict (TMB/GET)", "📊 Relatório Completo"])

with tab1:
    st.header("Registrar ingestão de alimentos")
    alimento = st.text_input("Alimento")
    quantidade = st.number_input("Quantidade (g)", min_value=1, value=100)
    if st.button("Calcular e Salvar"):
        try:
            r = requests.post(FUNCTION, params={"action": "calc"}, json={"alimento": alimento, "quantidade": quantidade}, timeout=15)
            if r.status_code == 200:
                st.success("Ingestão registrada!")
                st.json(r.json())
            else:
                st.error(f"Erro: {r.status_code} {r.text}")
        except Exception as e:
            st.error(str(e))

with tab2:
    st.header("Cálculo de TMB e GET — Harris Benedict")
    col1, col2 = st.columns(2)
    with col1:
        sexo = st.selectbox("Sexo", ["Masculino", "Feminino"])
        peso = st.number_input("Peso (kg)", min_value=1.0)
        altura = st.number_input("Altura (cm)", min_value=100.0)
        idade = st.number_input("Idade", min_value=1)
    with col2:
        atividade = st.selectbox("Nível de atividade", ["Sedentário","Leve","Moderado","Intenso","Muito Intenso"])
        nivel_api = {"Sedentário":"sedentario","Leve":"leve","Moderado":"moderado","Intenso":"intenso","Muito Intenso":"muito_intenso"}[atividade]
    if st.button("Calcular TMB/GET"):
        body = {"sexo": sexo, "peso": peso, "altura": altura, "idade": idade, "atividade": nivel_api}
        r = requests.post(FUNCTION, params={"action":"tmb"}, json=body, timeout=15)
        if r.status_code == 200:
            data = r.json()
            st.success("Calculado e salvo!")
            st.json(data)
            st.metric("TMB (kcal/dia)", f"{data['tmb']:.2f}")
            st.metric("GET (kcal/dia)", f"{data['get']:.2f}")
        else:
            st.error(r.text)

with tab3:
    st.header("Relatório completo — ingestão × gasto energético")
    if st.button("Carregar relatório"):
        r = requests.get(FUNCTION, params={"action":"relatorio"}, timeout=15)
        if r.status_code != 200:
            st.error(r.text)
        else:
            rep = r.json()
            st.subheader("Resumo")
            st.json(rep)
            if rep["balanco_calorico"] is not None:
                if rep["balanco_calorico"] > 0:
                    st.success(f"Superávit de {rep['balanco_calorico']:.2f} kcal")
                else:
                    st.warning(f"Déficit de {abs(rep['balanco_calorico']):.2f} kcal")
            if rep["dados_ingestao"]:
                df = pd.DataFrame(rep["dados_ingestao"])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values("timestamp")
                st.line_chart(df["calorias_totais"])
                st.dataframe(df)
            else:
                st.info("Nenhum registro de ingestão encontrado.")
