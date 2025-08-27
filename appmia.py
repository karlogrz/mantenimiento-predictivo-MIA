import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
from streamlit_lottie import st_lottie
import json
import requests

# Configuración de la página
st.set_page_config(
    page_title="🚗 Mantenimiento Predictivo Dinámico",
    layout="wide",
    page_icon="🔧"
)

# ---- Configuración de Telegram ----
TELEGRAM_TOKEN = "7991651835:AAE6ZPekhcddQs8yBc6Q0HzwBWaymfE-23c"
TELEGRAM_CHAT_ID = "6583159864"

def enviar_alerta_telegram(mensaje):
    """Envía un mensaje de alerta a Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            st.error(f"Error al enviar mensaje a Telegram: {response.text}")
        else:
            st.success("✅ Alerta enviada a Telegram")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

# ---- Carga de animación Lottie (opcional) ----
def load_lottie(filepath: str):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except:
        return None

# ---- Datos sintéticos en tiempo real ----
@st.cache_data
def generar_datos_sinteticos():
    np.random.seed(42)
    horas = np.arange(0, 24)
    datos = pd.DataFrame({
        "Hora": horas,
        "RPM": np.random.normal(2500, 300, 24),
        "Temperatura (°C)": np.random.normal(85, 10, 24)
    })
    return datos

# ---- Sidebar (Controles de usuario) ----
st.sidebar.header("🔧 Panel de Control")
umbral_temp = st.sidebar.slider("Umbral de temperatura crítica (°C)", 80, 120, 100)
variables = st.sidebar.multiselect(
    "Variables a visualizar",
    ["RPM", "Temperatura (°C)"],
    default=["Temperatura (°C)"]
)

# Configuración de Telegram en el sidebar
st.sidebar.header("🤖 Configuración de Telegram")
telegram_enabled = st.sidebar.checkbox("Activar alertas por Telegram", value=True)
if telegram_enabled:
    st.sidebar.success("✅ Alertas de Telegram activadas")
    st.sidebar.info(f"Chat ID: {TELEGRAM_CHAT_ID}")
else:
    st.sidebar.warning("❌ Alertas de Telegram desactivadas")

# Botón de prueba para Telegram
if st.sidebar.button("🧪 Probar Telegram"):
    mensaje_prueba = "🔧 Prueba de alerta desde Mantenimiento Predictivo\n✅ El bot está funcionando correctamente"
    enviar_alerta_telegram(mensaje_prueba)

# ---- Pestañas principales ----
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📅 Histórico", "⚙️ Simulador"])

with tab1:
    st.header("Monitoreo en Tiempo Real")
    
    # Gráfico dinámico (simulación de streaming)
    chart_placeholder = st.empty()
    status_placeholder = st.empty()
    datos = generar_datos_sinteticos()
    
    # Variables para controlar el envío de alertas
    alerta_temp_enviada = False
    
    for i in range(len(datos)):
        subset = datos.iloc[:i+1]
        fig = px.line(subset, x="Hora", y=variables, title="Tendencias en Tiempo Real")
        chart_placeholder.plotly_chart(fig, use_container_width=True)
        
        # Verificar alertas en cada iteración
        temp_actual = subset["Temperatura (°C)"].iloc[-1]
        hora_actual = subset["Hora"].iloc[-1]
        
        # Mostrar estado actual
        status_text = f"**Hora: {hora_actual}:00** | Temperatura: {temp_actual:.1f}°C | RPM: {subset['RPM'].iloc[-1]:.0f}"
        if temp_actual > umbral_temp:
            status_placeholder.error(f"🚨 {status_text} - ¡Temperatura crítica!")
        else:
            status_placeholder.success(f"✅ {status_text} - Normal")
        
        # Enviar alerta si se supera el umbral
        if telegram_enabled and temp_actual > umbral_temp and not alerta_temp_enviada:
            mensaje = f"🚨 ALERTA DE TEMPERATURA CRÍTICA\n\n• Valor actual: {temp_actual:.1f}°C\n• Umbral configurado: {umbral_temp}°C\n• Hora del evento: {hora_actual}:00\n• RPM: {subset['RPM'].iloc[-1]:.0f}"
            enviar_alerta_telegram(mensaje)
            alerta_temp_enviada = True
        
        time.sleep(0.5)  # Velocidad de actualización

with tab2:
    st.header("Análisis Histórico")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Datos completos")
        st.dataframe(datos, height=300)
    
    with col2:
        st.subheader("Estadísticas")
        st.metric("Temperatura máxima", f"{datos['Temperatura (°C)'].max():.1f}°C")
        st.metric("Temperatura promedio", f"{datos['Temperatura (°C)'].mean():.1f}°C")
        st.metric("RPM promedio", f"{datos['RPM'].mean():.0f}")
    
    # Gráfico interactivo
    st.subheader("Análisis de correlación")
    fig_hist = px.scatter(
        datos,
        x="RPM",
        y="Temperatura (°C)",
        color="Hora",
        title="Relación RPM vs Temperatura"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with tab3:
    st.header("Simulador de Fallos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Selector de fallos
        fallo = st.selectbox("Selecciona un fallo para simular:", 
                           ["Bujías", "Sobrecarga", "Fallo de refrigeración", "Filtro obstruido"])
        
        # Parámetros de simulación
        temp_simulacion = st.slider("Temperatura simulada (°C)", 50, 150, 110)
        
        if st.button("🔍 Simular fallo", type="primary"):
            if fallo == "Bujías":
                sintomas = "RPM inestables, aumento de temperatura"
                st.error(f"🚨 {sintomas}")
                if telegram_enabled:
                    mensaje = f"🔧 SIMULACIÓN: Fallo en Bujías\n• Síntomas: {sintomas}\n• Temperatura: {temp_simulacion}°C"
                    enviar_alerta_telegram(mensaje)
                    
            elif fallo == "Fallo de refrigeración":
                sintomas = "Temperatura elevada persistente, ventilador no funciona"
                st.warning(f"⚠️ {sintomas}")
                if telegram_enabled:
                    mensaje = f"🔧 SIMULACIÓN: Fallo de refrigeración\n• Síntomas: {sintomas}\n• Temperatura: {temp_simulacion}°C"
                    enviar_alerta_telegram(mensaje)
                    
            elif fallo == "Filtro obstruido":
                sintomas = "RPM bajas, temperatura variable"
                st.warning(f"⚠️ {sintomas}")
                if telegram_enabled:
                    mensaje = f"🔧 SIMULACIÓN: Filtro obstruido\n• Síntomas: {sintomas}\n• Temperatura: {temp_simulacion}°C"
                    enviar_alerta_telegram(mensaje)
                    
            else:  # Sobrecarga
                sintomas = "Temperatura > 110°C, pérdida de potencia"
                st.error(f"🚨 {sintomas}")
                if telegram_enabled:
                    mensaje = f"🔧 SIMULACIÓN: Sobrecarga del motor\n• Síntomas: {sintomas}\n• Temperatura: {temp_simulacion}°C"
                    enviar_alerta_telegram(mensaje)
    
    with col2:
        st.subheader("Información del fallo")
        if fallo == "Bujías":
            st.info("""
            **Fallo en bujías:**
            - Causa: Desgaste normal o contaminación
            - Solución: Reemplazar bujías
            - Frecuencia: Cada 30,000 km
            """)
        elif fallo == "Fallo de refrigeración":
            st.info("""
            **Fallo en sistema de refrigeración:**
            - Causa: Fuga de refrigerante o ventilador dañado
            - Solución: Reparar fugas, revisar ventilador
            - Verificar: Nivel de refrigerante
            """)
        elif fallo == "Filtro obstruido":
            st.info("""
            **Filtro de aire obstruido:**
            - Causa: Acumulación de suciedad
            - Solución: Reemplazar filtro de aire
            - Frecuencia: Cada 15,000 km
            """)
        else:
            st.info("""
            **Sobrecarga del motor:**
            - Causa: Exceso de carga o conducción agresiva
            - Solución: Reducir carga, revisar aceite
            - Prevención: Mantener ritmo de conducción suave
            """)

# ---- Alertas ----
st.sidebar.header("🚨 Alertas")
temp_maxima = datos["Temperatura (°C)"].max()
if temp_maxima > umbral_temp:
    st.sidebar.error(f"¡Alerta! Temperatura máxima: {temp_maxima}°C (Umbral: {umbral_temp}°C)")
else:
    st.sidebar.success(f"✅ Temperatura normal: {temp_maxima}°C")

# ---- Animación Lottie (opcional) ----
animacion = load_lottie("motor_animation.json")
if animacion:
    st_lottie(animacion, speed=1, height=200, key="motor")
else:
    st.info("⭐ Para añadir animaciones, sube un archivo JSON de Lottie llamado 'motor_animation.json'")

# ---- Botón de descarga ----
st.sidebar.download_button(
    "📥 Descargar Datos",
    datos.to_csv(),
    file_name="datos_motor.csv",
    mime="text/csv"
)

# ---- Información de conexión ----
with st.sidebar.expander("🔗 Estado de conexión"):
    st.write(f"**Token:** `{TELEGRAM_TOKEN[:10]}...`")
    st.write(f"**Chat ID:** `{TELEGRAM_CHAT_ID}`")
    st.write("**Estado:** ✅ Configurado correctamente")
    
    # Probamos la conexión
    if st.button("Probar conexión con Telegram"):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
            response = requests.get(url)
            if response.status_code == 200:
                st.success("✅ Conexión exitosa con Telegram")
            else:
                st.error("❌ Error en la conexión")
        except:
            st.error("❌ No se pudo conectar con Telegram")

# ---- Footer ----
st.markdown("---")
st.caption("Sistema de Mantenimiento Predictivo | Alertas enviadas a Telegram")