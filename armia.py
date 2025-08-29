import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
import requests
from datetime import datetime
import pytz
import serial
import serial.tools.list_ports

# --- Configuración de la página ---
st.set_page_config(
    page_title="🚗 Mantenimiento Predictivo Dinámico",
    layout="wide",
    page_icon="🔧"
)

# --- Configuración de Telegram ---
TELEGRAM_TOKEN = "7991651835:AAE6ZPekhcddQs8yBc6Q0HzwBWaymfE-23c"
TELEGRAM_CHAT_ID = "6583159864"

# --- Zona horaria ---
ZONA_HORARIA = pytz.timezone('America/Monterrey')

# --- Funciones ---
def obtener_fecha_hora_mty():
    ahora = datetime.now(ZONA_HORARIA)
    return ahora.strftime("%Y-%m-%d %H:%M:%S"), ahora.strftime("%A, %d de %B de %Y"), ahora.strftime("%H:%M:%S")

def listar_puertos_disponibles():
    puertos = list(serial.tools.list_ports.comports())
    return [p.device for p in puertos]

@st.cache_resource
def inicializar_serial(puerto):
    if puerto:
        try:
            ser = serial.Serial(puerto, 9600, timeout=1)
            time.sleep(2)
            ser.reset_input_buffer()
            return ser
        except Exception as e:
            st.error(f"Error al conectar con Arduino en {puerto}: {e}")
            return None
    return None

def leer_datos_arduino(ser):
    if ser and ser.in_waiting > 0:
        try:
            linea = ser.readline().decode('utf-8').strip()
            if linea:
                datos = {}
                if "RPM:" in linea:
                    rpm_part = linea.split("RPM:")[1].split("|")[0].strip()
                    datos['R'] = float(rpm_part) if rpm_part.replace('.', '').isdigit() else 0
                if "Temp:" in linea:
                    temp_part = linea.split("Temp:")[1].split("|")[0].strip().replace('C','')
                    datos['T'] = float(temp_part) if temp_part.replace('.', '').isdigit() else 0
                if "Vib:" in linea:
                    vib_part = linea.split("Vib:")[1].split("|")[0].strip().replace('m/s²','')
                    datos['V'] = float(vib_part) if vib_part.replace('.', '').isdigit() else 0
                return datos
        except Exception as e:
            st.error(f"Error al parsear datos: {e}")
    return None

def analizar_irregularidades_rpm(datos_rpm):
    irregularidades, fallos_probables = [], []
    if len(datos_rpm) > 0:
        media_rpm = np.mean(datos_rpm)
        std_rpm = np.std(datos_rpm)
        variacion = (std_rpm / media_rpm) * 100
        if variacion > 15:
            irregularidades.append(f"Alta variación en RPM ({variacion:.1f}%)")
            fallos_probables.extend(["Bujías desgastadas", "Problema de encendido", "Filtro de aire obstruido"])
        if any(rpm < 1000 for rpm in datos_rpm[-3:]):
            irregularidades.append("RPM muy bajas (<1000)")
            fallos_probables.extend(["Fallo de sensores", "Problema de combustible", "Filtro obstruido"])
        if any(rpm > 3200 for rpm in datos_rpm[-3:]):
            irregularidades.append("RPM muy altas (>3200)")
            fallos_probables.extend(["Fallo del acelerador", "Problema de transmisión", "Sobrecarga del motor"])
        if len(datos_rpm) > 5:
            ultimas_rpm = datos_rpm[-5:]
            diferencias = np.diff(ultimas_rpm)
            if np.std(diferencias) > 150:
                irregularidades.append("Patrón irregular en RPM")
                fallos_probables.extend(["Bujías defectuosas", "Bobinas de encendido", "Sensores dañados"])
    fallos_probables = list(set(fallos_probables))
    return irregularidades, fallos_probables

def predecir_fallo(temp_actual, rpm_actual, vib_actual, historial_rpm):
    irregularidades, fallos_probables = analizar_irregularidades_rpm(historial_rpm)
    if temp_actual > 100: fallos_probables.append("Fallo de refrigeración")
    if temp_actual > 110: fallos_probables.append("Sobrecarga del motor")
    if rpm_actual < 1500: fallos_probables.append("Problema de combustible")
    if rpm_actual > 3200: fallos_probables.append("Fallo del acelerador")
    if vib_actual > 4.0: fallos_probables.append("Desbalance en motor")
    if vib_actual > 3.0: fallos_probables.append("Problemas en rodamientos")
    fallos_probables = list(set(fallos_probables))
    if "Sobrecarga del motor" in fallos_probables:
        fallo_principal = "Sobrecarga del motor"
    elif "Fallo de refrigeración" in fallos_probables:
        fallo_principal = "Fallo de refrigeración"
    elif "Bujías desgastadas" in fallos_probables:
        fallo_principal = "Bujías desgastadas"
    elif "Desbalance en motor" in fallos_probables:
        fallo_principal = "Desbalance en motor"
    elif fallos_probables:
        fallo_principal = fallos_probables[0]
    else:
        fallo_principal = "Sin fallos detectados"
    return irregularidades, fallos_probables, fallo_principal

def enviar_alerta_telegram(mensaje, irregularidades=None, fallo_probable=None):
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    mensaje_completo = f"🕒 {fecha_formateada}\n⏰ Hora: {hora_actual}\n\n{mensaje}"
    if irregularidades:
        mensaje_completo += "\n\n🔍 Irregularidades detectadas:"
        for i in irregularidades:
            mensaje_completo += f"\n• {i}"
    if fallo_probable and fallo_probable != "Sin fallos detectados":
        mensaje_completo += f"\n\n⚠️ Fallo más probable: {fallo_probable}"
    if irregularidades or (fallo_probable and fallo_probable != "Sin fallos detectados"):
        mensaje_completo += "\n\n🔧 Recomendación: Verificar sistema inmediatamente"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje_completo, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload)
        if response.status_code != 200: st.error(f"Error Telegram: {response.text}")
    except Exception as e:
        st.error(f"Error de conexión Telegram: {e}")

# --- Sidebar ---
st.sidebar.header("🔧 Panel de Control")
fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
st.sidebar.info(f"📍 Monterrey, México\n📅 {fecha_formateada}\n🕒 {hora_actual}")

# --- Puerto Arduino ---
st.sidebar.header("🔌 Configuración de Puerto")
puertos_disponibles = listar_puertos_disponibles()
if puertos_disponibles:
    puerto_default = 'COM3' if 'COM3' in puertos_disponibles else puertos_disponibles[0]
    puerto_seleccionado = st.sidebar.selectbox("Seleccionar puerto Arduino:", puertos_disponibles, index=puertos_disponibles.index(puerto_default))
else:
    st.sidebar.warning("❌ No se detectaron puertos. Conecta Arduino y refresca.")

if st.sidebar.button("🔄 Actualizar lista de puertos"):
    puertos_disponibles = listar_puertos_disponibles()
    st.experimental_rerun()

# --- Inicializar Arduino ---
if 'ser' not in st.session_state:
    st.session_state.ser = inicializar_serial(puerto_seleccionado)

if st.sidebar.button("🔁 Reconectar Arduino"):
    st.session_state.ser = inicializar_serial(puerto_seleccionado)
    if st.session_state.ser:
        st.sidebar.success("✅ Reconexión exitosa")
    else:
        st.sidebar.error("❌ Error en la reconexión")

if st.session_state.ser is None:
    st.sidebar.error("❌ Arduino no conectado")
else:
    st.sidebar.success("✅ Arduino conectado")

# --- Monitoreo ---
st.sidebar.header("🚀 Control de Monitoreo")
if 'monitoreo_activo' not in st.session_state: st.session_state.monitoreo_activo = False
if st.sidebar.button("▶️ Iniciar") and st.session_state.ser:
    st.session_state.monitoreo_activo = True
    st.session_state.datos_reales = pd.DataFrame(columns=["Hora","RPM","Temperatura (°C)","Vibración (m/s²)"])
    st.session_state.historial_rpm = []
    st.sidebar.success("✅ Monitoreo iniciado")

if st.session_state.monitoreo_activo and st.sidebar.button("⏹️ Detener"):
    st.session_state.monitoreo_activo = False
    st.sidebar.warning("⏹️ Monitoreo detenido")

# --- Código principal de monitoreo en tiempo real ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard","📅 Histórico","⚙️ Configuración"])

with tab1:
    st.header("Monitoreo en Tiempo Real")
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.write(f"📍 Monterrey | 📅 {fecha_formateada} | 🕒 {hora_actual}")

    if not st.session_state.monitoreo_activo or st.session_state.ser is None:
        st.warning("⏸️ El monitoreo está detenido o Arduino no conectado.")
    else:
        chart_placeholder = st.empty()
        status_placeholder = st.empty()
        analisis_placeholder = st.empty()
        alerta_temp_enviada = alerta_rpm_alta_enviada = alerta_rpm_baja_enviada = alerta_vib_alta_enviada = False
        progress_bar = st.progress(0)
        status_text = st.empty()
        for i in range(100):
            if not st.session_state.monitoreo_activo: break
            datos = leer_datos_arduino(st.session_state.ser)
            if datos:
                hora_actual_num = datetime.now(ZONA_HORARIA).hour + datetime.now(ZONA_HORARIA).minute/60
                nuevo_dato = pd.DataFrame({
                    "Hora":[hora_actual_num],
                    "RPM":[datos.get('R',0)],
                    "Temperatura (°C)":[datos.get('T',0)],
                    "Vibración (m/s²)":[datos.get('V',0)]
                })
                st.session_state.datos_reales = pd.concat([st.session_state.datos_reales, nuevo_dato], ignore_index=True)
                if len(st.session_state.datos_reales) > 50: st.session_state.datos_reales = st.session_state.datos_reales.tail(50)
                fig = px.line(st.session_state.datos_reales, x="Hora", y=["RPM","Temperatura (°C)","Vibración (m/s²)"])
                chart_placeholder.plotly_chart(fig, use_container_width=True)
                temp_actual, rpm_actual, vib_actual = datos.get('T',0), datos.get('R',0), datos.get('V',0)
                st.session_state.historial_rpm.append(rpm_actual)
                if len(st.session_state.historial_rpm) > 10: st.session_state.historial_rpm = st.session_state.historial_rpm[-10:]
                irregularidades, fallos_probables, fallo_principal = predecir_fallo(temp_actual, rpm_actual, vib_actual, st.session_state.historial_rpm)
                status_text_display = f"Hora: {hora_actual} | Temp: {temp_actual:.1f}°C | RPM: {rpm_actual:.0f} | Vib: {vib_actual:.1f}"
                if irregularidades:
                    analisis_text = "Irregularidades detectadas:\n" + "\n".join([f"• {i}" for i in irregularidades]) + f"\nFallo probable: {fallo_principal}"
                    analisis_placeholder.warning(analisis_text)
                else:
                    analisis_placeholder.info("✅ Sin irregularidades")
            progress_bar.progress(i+1)
            status_text.text(f"Leyendo datos {i+1}/100")
            time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        st.success("✅ Monitoreo completado")
