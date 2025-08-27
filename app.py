import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
from streamlit_lottie import st_lottie
import json

# Configuración de la página
st.set_page_config(
    page_title="🚗 Mantenimiento Predictivo Dinámico",
    layout="wide",
    page_icon="🔧"
)

# ---- Carga de animación Lottie (opcional) ----
def load_lottie(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)

# ---- Datos sintéticos en tiempo real ----
@st.cache_data
def generar_datos_sinteticos():
    np.random.seed(42)
    horas = np.arange(0, 24)
    datos = pd.DataFrame({
        "Hora": horas,
        "RPM": np.random.normal(2500, 300, 24),
        "Temperatura (°C)": np.random.normal(85, 10, 24),
        "Vibración (g)": np.random.exponential(0.3, 24)
    })
    return datos

# ---- Sidebar (Controles de usuario) ----
st.sidebar.header("🔧 Panel de Control")
umbral_temp = st.sidebar.slider("Umbral de temperatura crítica (°C)", 80, 120, 100)
umbral_vib = st.sidebar.slider("Umbral de vibración crítica (g)", 0.1, 1.0, 0.5)
variables = st.sidebar.multiselect(
    "Variables a visualizar",
    ["RPM", "Temperatura (°C)", "Vibración (g)"],
    default=["Temperatura (°C)"]
)

# ---- Pestañas principales ----
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📅 Histórico", "⚙️ Simulador"])

with tab1:
    st.header("Monitoreo en Tiempo Real")
    
    # Gráfico dinámico (simulación de streaming)
    chart_placeholder = st.empty()
    datos = generar_datos_sinteticos()
    
    for i in range(len(datos)):
        subset = datos.iloc[:i+1]
        fig = px.line(subset, x="Hora", y=variables, title="Tendencias en Tiempo Real")
        chart_placeholder.plotly_chart(fig, use_container_width=True)
        time.sleep(0.5)  # Velocidad de actualización

with tab2:
    st.header("Análisis Histórico")
    st.dataframe(datos)
    
    # Gráfico interactivo
    fig_hist = px.scatter_matrix(
        datos,
        dimensions=["RPM", "Temperatura (°C)", "Vibración (g)"],
        color="Hora"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with tab3:
    st.header("Simulador de Fallos")
    
    # Selector de fallos
    fallo = st.selectbox("Selecciona un fallo para simular:", ["Bujías", "Rodamiento", "Sobrecarga"])
    
    if st.button("🔍 Mostrar síntomas"):
        if fallo == "Bujías":
            st.error("Síntomas: RPM inestables, aumento de temperatura")
        elif fallo == "Rodamiento":
            st.warning("Síntomas: Vibración > 0.8g, ruidos metálicos")
        else:
            st.error("Síntomas: Temperatura > 110°C, pérdida de potencia")

# ---- Alertas ----
st.sidebar.header("🚨 Alertas")
if (datos["Temperatura (°C)"] > umbral_temp).any():
    st.sidebar.error(f"¡Alerta! Temperatura superó {umbral_temp}°C")
if (datos["Vibración (g)"] > umbral_vib).any():
    st.sidebar.warning(f"¡Advertencia! Vibración superó {umbral_vib}g")

# ---- Animación Lottie (opcional) ----
# Descarga un JSON de animación desde: https://lottiefiles.com/
try:
    animacion = load_lottie("motor_animation.json")  # Archivo debe estar en tu repo
    st_lottie(animacion, speed=1, height=200, key="motor")
except:
    st.info("⭐ Para añadir animaciones, sube un archivo JSON de Lottie a tu repositorio")

# ---- Botón de descarga ----
st.sidebar.download_button(
    "📥 Descargar Datos",
    datos.to_csv(),
    file_name="datos_motor.csv",
    mime="text/csv"
)