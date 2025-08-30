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

# Configuración de la página con la paleta de colores
st.set_page_config(
    page_title="🚗 Mantenimiento Predictivo Dinámico",
    layout="wide",
    page_icon="🔧"
)

# ---- Configuración de Telegram ----
TELEGRAM_TOKEN = "7991651835:AAE6ZPekhcddQs8yBc6Q0HzwBWaymfE-23c"
TELEGRAM_CHAT_ID = "6583159864"

# ---- Paleta de colores personalizada ----
PALETA_COLORES = ['#006f75', '#00777e', '#015861', '#016c75', '#459ca3', '#f7f5f5', '#c5d3d5', '#abc4c7']

# ---- Aplicar estilos CSS con la paleta ----
st.markdown(f"""
<style>
    /* Colores principales */
    :root {{
        --color-primary: {PALETA_COLORES[0]};
        --color-secondary: {PALETA_COLORES[1]};
        --color-dark: {PALETA_COLORES[2]};
        --color-medium: {PALETA_COLORES[3]};
        --color-light: {PALETA_COLORES[4]};
        --color-background: {PALETA_COLORES[5]};
        --color-card: {PALETA_COLORES[6]};
        --color-border: {PALETA_COLORES[7]};
    }}
    
    /* Estilos generales */
    .stApp {{
        background-color: var(--color-background);
    }}
    
    /* Headers y títulos */
    h1, h2, h3, h4, h5, h6 {{
        color: var(--color-dark) !important;
        border-bottom: 2px solid var(--color-light);
        padding-bottom: 0.5rem;
    }}
    
    /* Sidebar */
    .css-1d391kg {{
        background-color: var(--color-card);
        border-right: 1px solid var(--color-border);
    }}
    
    .sidebar .sidebar-content {{
        background-color: var(--color-card);
    }}
    
    /* Botones */
    .stButton>button {{
        background-color: var(--color-primary);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }}
    
    .stButton>button:hover {{
        background-color: var(--color-dark);
        color: white;
    }}
    
    /* Cards y contenedores */
    .stMetric {{
        background-color: var(--color-card);
        border: 1px solid var(--color-border);
        border-radius: 10px;
        padding: 1rem;
    }}
    
    /* Dataframes */
    .dataframe {{
        border: 1px solid var(--color-border);
        border-radius: 8px;
    }}
    
    /* Progress bars */
    .stProgress > div > div {{
        background-color: var(--color-primary);
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background-color: var(--color-card);
        border: 1px solid var(--color-border);
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1rem;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: var(--color-primary);
        color: white;
    }}
    
    /* Alertas y mensajes */
    .stAlert {{
        border: 1px solid var(--color-border);
        border-radius: 8px;
    }}
    
    /* Inputs y selects */
    .stSelectbox, .stSlider, .stMultiselect {{
        background-color: var(--color-card);
        border: 1px solid var(--color-border);
        border-radius: 6px;
    }}
</style>
""", unsafe_allow_html=True)

# ---- Zona horaria de Monterrey, México ----
ZONA_HORARIA = pytz.timezone('America/Monterrey')

# ---- Función para encontrar puertos disponibles ----
def listar_puertos_disponibles():
    """Lista todos los puertos seriales disponibles"""
    try:
        puertos = serial.tools.list_ports.comports()
        return [p.device for p in puertos]
    except Exception as e:
        st.error(f"Error al listar puertos: {e}")
        return []

# ---- Configuración de conexión serial ----
@st.cache_resource
def inicializar_serial(puerto):
    """Inicializa la conexión serial con el puerto especificado"""
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

# ---- Función para simular datos del Arduino ----
def simular_datos_arduino():
    return {
        'R': np.random.randint(1500, 3000),
        'T': np.random.uniform(70, 95),
        'V': np.random.uniform(1.0, 3.5)
    }

# ---- Función para leer datos del Arduino ----
def leer_datos_arduino(ser, modo_simulacion=False):
    if modo_simulacion:
        time.sleep(0.5)
        return simular_datos_arduino()
    
    if ser and ser.in_waiting > 0:
        try:
            linea = ser.readline().decode('utf-8').strip()
            if linea:
                datos = {}
                
                if "RPM:" in linea:
                    rpm_part = linea.split("RPM:")[1].split("|")[0].strip()
                    datos['R'] = float(rpm_part) if rpm_part.replace('.', '').isdigit() else 0
                
                if "Temp:" in linea:
                    temp_part = linea.split("Temp:")[1].split("|")[0].strip()
                    if "ERROR" in temp_part:
                        datos['T'] = 0
                    else:
                        temp_part = temp_part.replace('C', '').strip()
                        datos['T'] = float(temp_part) if temp_part.replace('.', '').isdigit() else 0
                
                if "Vib:" in linea:
                    vib_part = linea.split("Vib:")[1].split("|")[0].strip()
                    vib_part = vib_part.replace('m/s²', '').strip()
                    datos['V'] = float(vib_part) if vib_part.replace('.', '').isdigit() else 0
                
                return datos
        except Exception as e:
            st.error(f"Error al parsear datos: {e}")
            return None
    return None

def obtener_fecha_hora_mty():
    ahora = datetime.now(ZONA_HORARIA)
    return ahora.strftime("%Y-%m-%d %H:%M:%S"), ahora.strftime("%A, %d de %B de %Y"), ahora.strftime("%H:%M:%S")

def analizar_irregularidades_rpm(datos_rpm):
    irregularidades = []
    fallos_probables = []
    
    if len(datos_rpm) > 0:
        media_rpm = np.mean(datos_rpm)
        std_rpm = np.std(datos_rpm) if len(datos_rpm) > 1 else 0
        variacion = (std_rpm / media_rpm) * 100 if media_rpm > 0 else 0
        
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
            if len(diferencias) > 0 and np.std(diferencias) > 150:
                irregularidades.append("Patrón irregular en RPM")
                fallos_probables.extend(["Bujías defectuosas", "Bobinas de encendido", "Sensores dañados"])
    
    fallos_probables = list(set(fallos_probables))
    return irregularidades, fallos_probables

def predecir_fallo(temp_actual, rpm_actual, vib_actual, historial_rpm):
    irregularidades, fallos_probables = analizar_irregularidades_rpm(historial_rpm)
    
    if temp_actual > 100:
        fallos_probables.append("Fallo de refrigeración")
    if temp_actual > 110:
        fallos_probables.append("Sobrecarga del motor")
    
    if rpm_actual < 1500:
        fallos_probables.append("Problema de combustible")
    if rpm_actual > 3200:
        fallos_probables.append("Fallo del acelerador")
    
    if vib_actual > 4.0:
        fallos_probables.append("Desbalance en motor")
    if vib_actual > 3.0:
        fallos_probables.append("Problemas en rodamientos")
    
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
        mensaje_completo += f"\n\n🔍 **Irregularidades detectadas:**"
        for irregularidad in irregularidades:
            mensaje_completo += f"\n• {irregularidad}"
    
    if fallo_probable and fallo_probable != "Sin fallos detectados":
        mensaje_completo += f"\n\n⚠️ **Fallo más probable:** {fallo_probable}"
    
    if irregularidades or (fallo_probable and fallo_probable != "Sin fallos detectados"):
        mensaje_completo += f"\n\n🔧 **Recomendación:** Verificar sistema inmediatamente"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje_completo,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            st.error(f"Error al enviar mensaje a Telegram: {response.text}")
        else:
            st.success("✅ Alerta enviada a Telegram")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

# ---- Inicializar variables de sesión ----
if 'monitoreo_activo' not in st.session_state:
    st.session_state.monitoreo_activo = False
if 'datos_reales' not in st.session_state:
    st.session_state.datos_reales = pd.DataFrame(columns=["Hora", "RPM", "Temperatura (°C)", "Vibración (m/s²)"])
if 'historial_rpm' not in st.session_state:
    st.session_state.historial_rpm = []
if 'ser' not in st.session_state:
    st.session_state.ser = None
if 'modo_simulacion' not in st.session_state:
    st.session_state.modo_simulacion = False

# ---- Sidebar con estilos personalizados ----
with st.sidebar:
    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]};'>
        <h2 style='color: {PALETA_COLORES[0]}; text-align: center;'>🔧 Panel de Control</h2>
    </div>
    """, unsafe_allow_html=True)
    
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.info(f"📍 **Monterrey, México**\n📅 {fecha_formateada}\n🕒 {hora_actual}")

    # ---- Modo de operación ----
    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin: 1rem 0;'>
        <h3 style='color: {PALETA_COLORES[0]};'>🔌 Modo de Operación</h3>
    </div>
    """, unsafe_allow_html=True)
    
    modo_simulacion = st.checkbox("📱 Usar modo simulación", value=True)
    st.session_state.modo_simulacion = modo_simulacion

    if not modo_simulacion:
        st.markdown(f"""
        <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin: 1rem 0;'>
            <h3 style='color: {PALETA_COLORES[0]};'>🔌 Configuración de Puerto</h3>
        </div>
        """, unsafe_allow_html=True)
        
        puertos_disponibles = listar_puertos_disponibles()
        
        if not puertos_disponibles:
            st.warning("❌ No se detectaron puertos seriales")
            st.info("💡 Conecta el Arduino y verifica los controladores")
            st.session_state.modo_simulacion = True
            modo_simulacion = True
        else:
            puerto_default = 'COM3' if 'COM3' in puertos_disponibles else puertos_disponibles[0]
            puerto_seleccionado = st.selectbox(
                "Seleccionar puerto Arduino:",
                options=puertos_disponibles,
                index=puertos_disponibles.index(puerto_default)
            )
            
            st.success(f"✅ {len(puertos_disponibles)} puerto(s) detectado(s)")

            if st.button("🔌 Conectar Arduino", use_container_width=True):
                st.session_state.ser = inicializar_serial(puerto_seleccionado)
                if st.session_state.ser:
                    st.success("✅ Conexión exitosa")
                else:
                    st.error("❌ Error en la conexión")

            if st.session_state.ser:
                st.success("✅ Arduino conectado")
            else:
                st.info("💡 Haz clic en 'Conectar Arduino'")
    else:
        st.success("📱 Modo simulación activado")
        st.info("Los datos se generarán automáticamente")

    # ---- Botón de Iniciar Monitoreo ----
    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin: 1rem 0;'>
        <h3 style='color: {PALETA_COLORES[0]};'>🚀 Control de Monitoreo</h3>
    </div>
    """, unsafe_allow_html=True)

    if st.button("▶️ Iniciar Monitoreo", type="primary", use_container_width=True):
        st.session_state.monitoreo_activo = True
        st.session_state.datos_reales = pd.DataFrame(columns=["Hora", "RPM", "Temperatura (°C)", "Vibración (m/s²)"])
        st.session_state.historial_rpm = []
        st.success("✅ Monitoreo iniciado")

    if st.session_state.monitoreo_activo:
        st.info("🔴 Monitoreo en curso...")
        if st.button("⏹️ Detener Monitoreo", use_container_width=True):
            st.session_state.monitoreo_activo = False
            st.warning("⏹️ Monitoreo detenido")

    # ---- Controles de configuración ----
    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin: 1rem 0;'>
        <h3 style='color: {PALETA_COLORES[0]};'>🌡️ Configuración de Umbrales</h3>
    </div>
    """, unsafe_allow_html=True)
    
    umbral_temp_min = st.slider("Umbral mínimo de temperatura (°C)", 60, 90, 70)
    umbral_temp_max = st.slider("Umbral máximo de temperatura crítica (°C)", 80, 120, 100)
    umbral_rpm_min = st.slider("Umbral mínimo de RPM", 1500, 2200, 1800)
    umbral_rpm_max = st.slider("Umbral máximo de RPM", 2800, 3500, 3200)
    umbral_vib_medio = st.slider("Umbral medio de vibración (m/s²)", 2.0, 4.0, 2.0)
    umbral_vib_alto = st.slider("Umbral alto de vibración (m/s²)", 3.0, 5.0, 4.0)

    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin: 1rem 0;'>
        <h3 style='color: {PALETA_COLORES[0]};'>📊 Visualización</h3>
    </div>
    """, unsafe_allow_html=True)
    
    variables = st.multiselect(
        "Variables a visualizar",
        ["RPM", "Temperatura (°C)", "Vibración (m/s²)"],
        default=["Temperatura (°C)", "RPM", "Vibración (m/s²)"]
    )

    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin: 1rem 0;'>
        <h3 style='color: {PALETA_COLORES[0]};'>🤖 Configuración de Telegram</h3>
    </div>
    """, unsafe_allow_html=True)
    
    telegram_enabled = st.checkbox("Activar alertas por Telegram", value=True)

    if st.button("🧪 Probar Telegram", use_container_width=True):
        irregularidades = ["Alta variación en RPM (18.2%)", "Patrón irregular detectado"]
        fallo_probable = "Bujías desgastadas"
        mensaje_prueba = f"🔧 Prueba de alerta desde Mantenimiento Predictivo\n📍 Monterrey, México\n✅ Sistema de detección de fallos activado"
        enviar_alerta_telegram(mensaje_prueba, irregularidades, fallo_probable)

# ---- Pestañas principales ----
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📅 Histórico", "⚙️ Configuración"])

with tab1:
    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin-bottom: 1rem;'>
        <h1 style='color: {PALETA_COLORES[0]}; text-align: center;'>📊 Monitoreo en Tiempo Real</h1>
    </div>
    """, unsafe_allow_html=True)
    
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.write(f"**📍 Ubicación:** Monterrey, México | **📅 Fecha:** {fecha_formateada} | **🕒 Hora:** {hora_actual}")
    
    if st.session_state.modo_simulacion:
        st.info("📱 **Modo simulación activado** - Los datos se generan automáticamente para pruebas")
    
    if not st.session_state.monitoreo_activo:
        st.warning("⏸️ El monitoreo está detenido. Presiona 'Iniciar Monitoreo' para comenzar.")
    else:
        chart_placeholder = st.empty()
        status_placeholder = st.empty()
        analisis_placeholder = st.empty()
        
        alerta_temp_enviada = False
        alerta_rpm_alta_enviada = False
        alerta_rpm_baja_enviada = False
        alerta_vib_alta_enviada = False
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(50):
            if not st.session_state.monitoreo_activo:
                break
                
            datos_arduino = leer_datos_arduino(st.session_state.ser, st.session_state.modo_simulacion)
            
            if datos_arduino:
                fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
                hora_actual_num = datetime.now(ZONA_HORARIA).hour + datetime.now(ZONA_HORARIA).minute/60
                
                nuevo_dato = pd.DataFrame({
                    "Hora": [hora_actual_num],
                    "RPM": [datos_arduino.get('R', 0)],
                    "Temperatura (°C)": [datos_arduino.get('T', 0)],
                    "Vibración (m/s²)": [datos_arduino.get('V', 0)]
                })
                
                st.session_state.datos_reales = pd.concat([st.session_state.datos_reales, nuevo_dato], ignore_index=True)
                
                if len(st.session_state.datos_reales) > 30:
                    st.session_state.datos_reales = st.session_state.datos_reales.tail(30)
                
                if not st.session_state.datos_reales.empty:
                    datos_limpios = st.session_state.datos_reales.copy()
                    
                    for col in variables:
                        if col in datos_limpios.columns:
                            datos_limpios[col] = pd.to_numeric(datos_limpios[col], errors='coerce').fillna(0)
                    
                    fig = px.line(datos_limpios, x="Hora", y=variables, 
                                 title="Tendencias en Tiempo Real - Datos desde Arduino",
                                 color_discrete_sequence=PALETA_COLORES)
                    chart_placeholder.plotly_chart(fig, use_container_width=True)
                
                temp_actual = datos_arduino.get('T', 0)
                rpm_actual = datos_arduino.get('R', 0)
                vib_actual = datos_arduino.get('V', 0)
                
                st.session_state.historial_rpm.append(rpm_actual)
                if len(st.session_state.historial_rpm) > 10:
                    st.session_state.historial_rpm = st.session_state.historial_rpm[-10:]
                
                irregularidades, fallos_probables, fallo_principal = predecir_fallo(
                    temp_actual, rpm_actual, vib_actual, st.session_state.historial_rpm
                )
                
                status_text_display = f"**Hora: {hora_actual}** | Temperatura: {temp_actual:.1f}°C | RPM: {rpm_actual:.0f} | Vibración: {vib_actual:.1f} m/s²"
                
                if irregularidades:
                    analisis_text = "🔍 **Irregularidades detectadas:**\n"
                    for irregularidad in irregularidades:
                        analisis_text += f"• {irregularidad}\n"
                    analisis_text += f"⚠️ **Fallo probable:** {fallo_principal}"
                    analisis_placeholder.warning(analisis_text)
                else:
                    analisis_placeholder.info("✅ No se detectaron irregularidades")
                
                if (temp_actual > umbral_temp_max or rpm_actual > umbral_rpm_max or 
                    rpm_actual < umbral_rpm_min or vib_actual > umbral_vib_alto):
                    status_placeholder.error(f"🚨 {status_text_display} - ¡Condición crítica!")
                elif (temp_actual > umbral_temp_min or vib_actual > umbral_vib_medio or irregularidades):
                    status_placeholder.warning(f"⚠️ {status_text_display} - Advertencia")
                else:
                    status_placeholder.success(f"✅ {status_text_display} - Normal")
                
                if telegram_enabled:
                    if temp_actual > umbral_temp_max and not alerta_temp_enviada:
                        mensaje = f"🚨 ALERTA: Temperatura crítica detectada\n\n• Valor actual: {temp_actual:.1f}°C\n• Umbral máximo: {umbral_temp_max}°C"
                        enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                        alerta_temp_enviada = True
                    
                    if rpm_actual > umbral_rpm_max and not alerta_rpm_alta_enviada:
                        mensaje = f"🚨 ALERTA: RPM críticas detectadas\n\n• Valor actual: {rpm_actual:.0f} RPM\n• Umbral máximo: {umbral_rpm_max} RPM"
                        enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                        alerta_rpm_alta_enviada = True
            
            progress_bar.progress((i + 1) / 50)
            status_text.text(f"Leyendo datos: {i + 1}/50")
            time.sleep(1)
        
        progress_bar.empty()
        status_text.empty()
        if st.session_state.monitoreo_activo:
            st.success("✅ Monitoreo completado")

with tab2:
    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin-bottom: 1rem;'>
        <h1 style='color: {PALETA_COLORES[0]}; text-align: center;'>📅 Análisis Histórico</h1>
    </div>
    """, unsafe_allow_html=True)
    
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.write(f"**📍 Ubicación:** Monterrey, México | **📅 Fecha del reporte:** {fecha_formateada}")
    
    if 'datos_reales' in st.session_state and len(st.session_state.datos_reales) > 0:
        datos = st.session_state.datos_reales
        
        datos_limpios = datos.copy()
        for col in ["RPM", "Temperatura (°C)", "Vibración (m/s²)"]:
            if col in datos_limpios.columns:
                datos_limpios[col] = pd.to_numeric(datos_limpios[col], errors='coerce').fillna(0)
        
        st.subheader("🔍 Análisis de Irregularidades")
        if 'historial_rpm' in st.session_state and len(st.session_state.historial_rpm) > 0:
            irregularidades, fallos_probables = analizar_irregularidades_rpm(st.session_state.historial_rpm)
            
            if irregularidades:
                st.warning("**Irregularidades detectadas:**")
                for irregularidad in irregularidades:
                    st.write(f"• {irregularidad}")
                st.error("**Fallos probables:**")
                for fallo in fallos_probables:
                    st.write(f"• {fallo}")
            else:
                st.success("✅ No se detectaron irregularidades significativas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Datos completos")
            st.dataframe(datos_limpios, height=300)
        
        with col2:
            st.subheader("Estadísticas")
            if "Temperatura (°C)" in datos_limpios.columns:
                st.metric("Temperatura máxima", f"{datos_limpios['Temperatura (°C)'].max():.1f}°C")
                st.metric("Temperatura promedio", f"{datos_limpios['Temperatura (°C)'].mean():.1f}°C")
            if "RPM" in datos_limpios.columns and len(datos_limpios["RPM"]) > 0:
                st.metric("RPM máximo", f"{datos_limpios['RPM'].max():.0f}")
                st.metric("RPM promedio", f"{datos_limpios['RPM'].mean():.0f}")
                st.metric("RPM mínimo", f"{datos_limpios['RPM'].min():.0f}")
        
        if "RPM" in datos_limpios.columns and "Temperatura (°C)" in datos_limpios.columns:
            fig_hist = px.scatter(
                datos_limpios,
                x="RPM",
                y="Temperatura (°C)",
                color="Vibración (m/s²)" if "Vibración (m/s²)" in datos_limpios.columns else None,
                title="Relación RPM vs Temperatura - Análisis Histórico",
                color_continuous_scale=PALETA_COLORES
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No hay datos históricos disponibles. Inicia el monitoreo para recopilar datos.")

with tab3:
    st.markdown(f"""
    <div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; margin-bottom: 1rem;'>
        <h1 style='color: {PALETA_COLORES[0]}; text-align: center;'>⚙️ Configuración del Sistema</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Estado del Sistema")
    if st.session_state.modo_simulacion:
        st.success("📱 Modo simulación activado")
        st.info("Los datos se generan automáticamente para pruebas")
    elif st.session_state.ser:
        st.success("✅ Arduino conectado correctamente")
    else:
        st.error("❌ Arduino no conectado")
        st.write("**Solución de problemas:**")
        st.write("1. Verifica que el Arduino esté conectado por USB")
        st.write("2. Asegúrate de que el sketch esté cargado correctamente")
        st.write("3. Reinicia el Arduino si es necesario")
        st.write("4. Verifica que el puerto COM esté disponible")
    
    st.subheader("🎨 Paleta de Colores")
    st.write("**Colores actuales de la aplicación:**")
    
    # Mostrar la paleta de colores
    cols = st.columns(8)
    nombres_colores = ["Primary", "Secondary", "Dark", "Medium", "Light", "Background", "Card", "Border"]
    
    for i, (col, nombre, color) in enumerate(zip(cols, nombres_colores, PALETA_COLORES)):
        with col:
            st.markdown(f"""
            <div style='background-color: {color}; padding: 1rem; border-radius: 8px; text-align: center; color: {'white' if i < 5 else 'black'};'>
                <strong>{nombre}</strong><br>{color}
            </div>
            """, unsafe_allow_html=True)
    
    st.subheader("Configuración de Telegram")
    st.write(f"**Token:** {TELEGRAM_TOKEN[:10]}...")
    st.write(f"**Chat ID:** {TELEGRAM_CHAT_ID}")
    st.write("**Estado:** ✅ Configurado correctamente" if telegram_enabled else "**Estado:** ❌ Desactivado")
    
    if st.button("Probar conexión con Telegram"):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
            response = requests.get(url)
            if response.status_code == 200:
                st.success("✅ Conexión exitosa con Telegram")
            else:
                st.error("❌ Error en la conexión con Telegram")
        except:
            st.error("❌ No se pudo conectar con Telegram")

# ---- Footer ----
st.markdown("---")
st.markdown(f"""
<div style='background-color: {PALETA_COLORES[6]}; padding: 1rem; border-radius: 10px; border: 1px solid {PALETA_COLORES[7]}; text-align: center;'>
    <p style='color: {PALETA_COLORES[0]}; margin: 0;'>Sistema de Mantenimiento Predictivo | 📍 Monterrey, México | Alertas enviadas a Telegram</p>
</div>
""", unsafe_allow_html=True)