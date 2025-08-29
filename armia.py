import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
from datetime import datetime
import pytz
import serial
import serial.tools.list_ports
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

# ---- Zona horaria de Monterrey, México ----
ZONA_HORARIA = pytz.timezone('America/Monterrey')

# Inicializar estado de sesión
if 'monitoreo_activo' not in st.session_state:
    st.session_state.monitoreo_activo = False
if 'datos_reales' not in st.session_state:
    st.session_state.datos_reales = pd.DataFrame(columns=["Hora", "RPM", "Temperatura (°C)", "Vibración (m/s²)"])
if 'historial_rpm' not in st.session_state:
    st.session_state.historial_rpm = []
if 'ser' not in st.session_state:
    st.session_state.ser = None
if 'ultima_lectura' not in st.session_state:
    st.session_state.ultima_lectura = {"RPM": 0, "Temperatura": 0, "Vibración": 0}
if 'puerto_actual' not in st.session_state:
    st.session_state.puerto_actual = None

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
def conectar_arduino(puerto):
    """Intenta conectar con Arduino en el puerto especificado"""
    if not puerto:
        return None
        
    try:
        # Cerrar conexión existente si hay una
        if st.session_state.ser and st.session_state.ser.is_open:
            st.session_state.ser.close()
            time.sleep(1)
            
        # Intentar nueva conexión
        ser = serial.Serial(puerto, 9600, timeout=1)
        time.sleep(2)  # Esperar a que se establezca la conexión
        ser.reset_input_buffer()
        st.session_state.puerto_actual = puerto
        return ser
    except Exception as e:
        st.error(f"Error al conectar con Arduino en {puerto}: {e}")
        return None

# ---- Función para leer datos del Arduino ----
def leer_datos_arduino(ser):
    if ser and ser.is_open and ser.in_waiting > 0:
        try:
            linea = ser.readline().decode('utf-8').strip()
            if linea:
                # Parsear datos del formato: "RPM: 1234 | Temp: 25.5C | Vib: 2.3 m/s² | SIN VIBRACION"
                datos = {}
                
                # Extraer RPM
                if "RPM:" in linea:
                    rpm_part = linea.split("RPM:")[1].split("|")[0].strip()
                    datos['R'] = float(rpm_part) if rpm_part.replace('.', '').isdigit() else 0
                
                # Extraer Temperatura
                if "Temp:" in linea:
                    temp_part = linea.split("Temp:")[1].split("|")[0].strip()
                    if "ERROR" in temp_part:
                        datos['T'] = 0
                    else:
                        temp_part = temp_part.replace('C', '').strip()
                        datos['T'] = float(temp_part) if temp_part.replace('.', '').isdigit() else 0
                
                # Extraer Vibración
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
    """Obtiene la fecha y hora actual de Monterrey, México"""
    ahora = datetime.now(ZONA_HORARIA)
    return ahora.strftime("%Y-%m-%d %H:%M:%S"), ahora.strftime("%A, %d de %B de %Y"), ahora.strftime("%H:%M:%S")

def analizar_irregularidades_rpm(datos_rpm):
    """Analiza irregularidades en las RPM y sugiere fallos probables"""
    irregularidades = []
    fallos_probables = []
    
    # Calcular estadísticas
    if len(datos_rpm) > 0:
        media_rpm = np.mean(datos_rpm)
        std_rpm = np.std(datos_rpm)
        variacion = (std_rpm / media_rpm) * 100  # Variación porcentual
        
        # Detectar irregularidades
        if variacion > 15:
            irregularidades.append(f"Alta variación en RPM ({variacion:.1f}%)")
            fallos_probables.extend(["Bujías desgastadas", "Problema de encendido", "Filtro de aire obstruido"])
        
        if any(rpm < 1000 for rpm in datos_rpm[-3:]):  # Últimas 3 mediciones
            irregularidades.append("RPM muy bajas (<1000)")
            fallos_probables.extend(["Fallo de sensores", "Problema de combustible", "Filtro obstruido"])
        
        if any(rpm > 3200 for rpm in datos_rpm[-3:]):
            irregularidades.append("RPM muy altas (>3200)")
            fallos_probables.extend(["Fallo del acelerador", "Problema de transmisión", "Sobrecarga del motor"])
        
        # Detectar patrones irregulares
        if len(datos_rpm) > 5:
            ultimas_rpm = datos_rpm[-5:]
            diferencias = np.diff(ultimas_rpm)
            if np.std(diferencias) > 150:
                irregularidades.append("Patrón irregular en RPM")
                fallos_probables.extend(["Bujías defectuosas", "Bobinas de encendido", "Sensores dañados"])
    
    # Eliminar duplicados
    fallos_probables = list(set(fallos_probables))
    
    return irregularidades, fallos_probables

def predecir_fallo(temp_actual, rpm_actual, vib_actual, historial_rpm):
    """Predice el fallo más probable basado en los datos actuales"""
    irregularidades, fallos_probables = analizar_irregularidades_rpm(historial_rpm)
    
    # Basado en temperatura
    if temp_actual > 100:
        fallos_probables.append("Fallo de refrigeración")
    if temp_actual > 110:
        fallos_probables.append("Sobrecarga del motor")
    
    # Basado en RPM
    if rpm_actual < 1500:
        fallos_probables.append("Problema de combustible")
    if rpm_actual > 3200:
        fallos_probables.append("Fallo del acelerador")
    
    # Basado en vibración
    if vib_actual > 4.0:
        fallos_probables.append("Desbalance en motor")
    if vib_actual > 3.0:
        fallos_probables.append("Problemas en rodamientos")
    
    # Eliminar duplicados y priorizar
    fallos_probables = list(set(fallos_probables))
    
    # Priorizar fallos basados en severidad
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
    """Envía un mensaje de alerta a Telegram con análisis de fallos"""
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    
    # Construir mensaje completo
    mensaje_completo = f"🕒 {fecha_formateada}\n⏰ Hora: {hora_actual}\n\n{mensaje}"
    
    # Añadir análisis de irregularidades si existe
    if irregularidades:
        mensaje_completo += f"\n\n🔍 **Irregularidades detectadas:**"
        for irregularidad in irregularidades:
            mensaje_completo += f"\n• {irregularidad}"
    
    # Añadir fallo probable si existe
    if fallo_probable and fallo_probable != "Sin fallos detectados":
        mensaje_completo += f"\n\n⚠️ **Fallo más probable:** {fallo_probable}"
    
    # Añadir recomendación
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

# ---- Sidebar (Controles de usuario) ----
st.sidebar.header("🔧 Panel de Control")

# Mostrar hora actual de Monterrey
fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
st.sidebar.info(f"📍 Monterrey, México\n📅 {fecha_formateada}\n🕒 {hora_actual}")

# ---- Selector manual de puerto Arduino ----
st.sidebar.header("🔌 Configuración de Puerto")

# Listar puertos disponibles
puertos_disponibles = listar_puertos_disponibles()
puerto_default = None

if puertos_disponibles:
    # Intentar encontrar el puerto actualmente conectado
    if st.session_state.puerto_actual and st.session_state.puerto_actual in puertos_disponibles:
        puerto_default = st.session_state.puerto_actual
    else:
        # Buscar puertos comunes de Arduino
        for puerto in puertos_disponibles:
            if 'COM3' in puerto or 'COM4' in puerto or 'ttyUSB' in puerto or 'ttyACM' in puerto:
                puerto_default = puerto
                break
        # Si no se encuentra uno común, usar el primero
        if not puerto_default and puertos_disponibles:
            puerto_default = puertos_disponibles[0]

puerto_seleccionado = st.sidebar.selectbox(
    "Seleccionar puerto Arduino:",
    options=puertos_disponibles,
    index=puertos_disponibles.index(puerto_default) if puerto_default and puertos_disponibles else 0,
    help="Selecciona el puerto COM donde está conectado tu Arduino"
)

# Botón para conectar/desconectar
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🔌 Conectar", use_container_width=True):
        st.session_state.ser = conectar_arduino(puerto_seleccionado)
        if st.session_state.ser:
            st.sidebar.success("✅ Conectado al Arduino")
        else:
            st.sidebar.error("❌ Error de conexión")

with col2:
    if st.button("🔓 Desconectar", use_container_width=True):
        if st.session_state.ser and st.session_state.ser.is_open:
            st.session_state.ser.close()
        st.session_state.ser = None
        st.session_state.puerto_actual = None
        st.sidebar.info("🔓 Arduino desconectado")

# Mostrar estado de conexión
if st.session_state.ser and st.session_state.ser.is_open:
    st.sidebar.success(f"✅ Conectado a {st.session_state.puerto_actual}")
else:
    st.sidebar.error("❌ Arduino no conectado")

# Botón para actualizar lista de puertos
if st.sidebar.button("🔄 Actualizar lista de puertos", use_container_width=True):
    puertos_disponibles = listar_puertos_disponibles()
    st.sidebar.info("Lista de puertos actualizada")

# Botón de Iniciar/Detener Monitoreo
st.sidebar.header("🚀 Control de Monitoreo")

if st.sidebar.button("▶️ Iniciar Monitoreo", type="primary", use_container_width=True):
    if st.session_state.ser and st.session_state.ser.is_open:
        st.session_state.monitoreo_activo = True
        st.session_state.datos_reales = pd.DataFrame(columns=["Hora", "RPM", "Temperatura (°C)", "Vibración (m/s²)"])
        st.session_state.historial_rpm = []
        st.sidebar.success("✅ Monitoreo iniciado")
    else:
        st.sidebar.error("❌ Conecta el Arduino primero")

if st.session_state.monitoreo_activo:
    if st.sidebar.button("⏹️ Detener Monitoreo", use_container_width=True):
        st.session_state.monitoreo_activo = False
        st.sidebar.warning("⏹️ Monitoreo detenido")

# Controles para Temperatura
st.sidebar.header("🌡️ Configuración de Umbrales")
umbral_temp_min = st.sidebar.slider("Umbral mínimo de temperatura (°C)", 60, 90, 70)
umbral_temp_max = st.sidebar.slider("Umbral máximo de temperatura crítica (°C)", 80, 120, 100)

# Controles para RPM
st.sidebar.subheader("⚙️ Control de RPM")
umbral_rpm_min = st.sidebar.slider("Umbral mínimo de RPM", 1500, 2200, 1800)
umbral_rpm_max = st.sidebar.slider("Umbral máximo de RPM", 2800, 3500, 3200)

# Controles para Vibración
st.sidebar.subheader("📳 Control de Vibración")
umbral_vib_medio = st.sidebar.slider("Umbral medio de vibración (m/s²)", 2.0, 4.0, 2.0)
umbral_vib_alto = st.sidebar.slider("Umbral alto de vibración (m/s²)", 3.0, 5.0, 4.0)

# Selector de variables a visualizar
st.sidebar.subheader("📊 Visualización")
variables = st.sidebar.multiselect(
    "Variables a visualizar",
    ["RPM", "Temperatura (°C)", "Vibración (m/s²)"],
    default=["Temperatura (°C)", "RPM", "Vibración (m/s²)"]
)

# Configuración de Telegram en el sidebar
st.sidebar.header("🤖 Configuración de Telegram")
telegram_enabled = st.sidebar.checkbox("Activar alertas por Telegram", value=True)
if telegram_enabled:
    st.sidebar.success("✅ Alertas de Telegram activadas")
else:
    st.sidebar.warning("❌ Alertas de Telegram desactivadas")

# Botón de prueba para Telegram
if st.sidebar.button("🧪 Probar Telegram"):
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    # Simular análisis de irregularidades para la prueba
    irregularidades = ["Alta variación en RPM (18.2%)", "Patrón irregular detectado"]
    fallo_probable = "Bujías desgastadas"
    mensaje_prueba = f"🔧 Prueba de alerta desde Mantenimiento Predictivo\n📍 Monterrey, México\n✅ Sistema de detección de fallos activado"
    enviar_alerta_telegram(mensaje_prueba, irregularidades, fallo_probable)

# ---- Pestañas principales ----
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📅 Histórico", "⚙️ Configuración"])

with tab1:
    st.header("Monitoreo en Tiempo Real")
    
    # Mostrar hora actual
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.write(f"**📍 Ubicación:** Monterrey, México | **📅 Fecha:** {fecha_formateada} | **🕒 Hora:** {hora_actual}")
    
    if not st.session_state.monitoreo_activo or st.session_state.ser is None:
        st.warning("⏸️ El monitoreo está detenido o Arduino no conectado. Presiona 'Iniciar' en el panel de control para comenzar.")
        st.info("💡 Configure los umbrales y visualización antes de iniciar el monitoreo.")
    else:
        # Contenedores para la interfaz
        chart_placeholder = st.empty()
        status_placeholder = st.empty()
        analisis_placeholder = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Variables para controlar el envío de alertas
        alerta_temp_enviada = False
        alerta_rpm_alta_enviada = False
        alerta_rpm_baja_enviada = False
        alerta_vib_alta_enviada = False
        
        # Realizar 20 lecturas (en lugar de 100 para no bloquear la interfaz)
        for i in range(20):
            if not st.session_state.monitoreo_activo:
                st.warning("Monitoreo detenido por el usuario")
                break
                
            # Verificar que el Arduino siga conectado
            if not st.session_state.ser or not st.session_state.ser.is_open:
                st.error("❌ Arduino desconectado durante el monitoreo")
                st.session_state.monitoreo_activo = False
                break
                
            # Leer datos del Arduino
            datos_arduino = leer_datos_arduino(st.session_state.ser)
            
            if datos_arduino:
                # Obtener fecha y hora actual para Monterrey
                fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
                hora_actual_num = datetime.now(ZONA_HORARIA).hour + datetime.now(ZONA_HORARIA).minute/60
                
                # Agregar nuevos datos al DataFrame
                nuevo_dato = pd.DataFrame({
                    "Hora": [hora_actual_num],
                    "RPM": [datos_arduino.get('R', 0)],
                    "Temperatura (°C)": [datos_arduino.get('T', 0)],
                    "Vibración (m/s²)": [datos_arduino.get('V', 0)]
                })
                
                st.session_state.datos_reales = pd.concat([st.session_state.datos_reales, nuevo_dato], ignore_index=True)
                
                # Mantener solo los últimos 50 puntos de datos
                if len(st.session_state.datos_reales) > 50:
                    st.session_state.datos_reales = st.session_state.datos_reales.tail(50)
                
                # Actualizar gráfico
                if not st.session_state.datos_reales.empty:
                    fig = px.line(st.session_state.datos_reales, x="Hora", y=variables, 
                                 title="Tendencias en Tiempo Real - Datos Reales desde Arduino")
                    chart_placeholder.plotly_chart(fig, use_container_width=True)
                
                # Obtener valores actuales
                temp_actual = datos_arduino.get('T', 0)
                rpm_actual = datos_arduino.get('R', 0)
                vib_actual = datos_arduino.get('V', 0)
                
                # Guardar última lectura
                st.session_state.ultima_lectura = {
                    "RPM": rpm_actual,
                    "Temperatura": temp_actual,
                    "Vibración": vib_actual
                }
                
                # Actualizar historial de RPM para análisis
                st.session_state.historial_rpm.append(rpm_actual)
                if len(st.session_state.historial_rpm) > 10:  # Mantener solo últimas 10 mediciones
                    st.session_state.historial_rpm = st.session_state.historial_rpm[-10:]
                
                # Analizar irregularidades
                irregularidades, fallos_probables, fallo_principal = predecir_fallo(
                    temp_actual, rpm_actual, vib_actual, st.session_state.historial_rpm
                )
                
                # Mostrar estado actual
                status_text_display = f"**Hora: {hora_actual}** | Temperatura: {temp_actual:.1f}°C | RPM: {rpm_actual:.0f} | Vibración: {vib_actual:.1f} m/s²"
                
                # Mostrar análisis de irregularidades
                if irregularidades:
                    analisis_text = "🔍 **Irregularidades detectadas:**\n"
                    for irregularidad in irregularidades:
                        analisis_text += f"• {irregularidad}\n"
                    analisis_text += f"⚠️ **Fallo probable:** {fallo_principal}"
                    analisis_placeholder.warning(analisis_text)
                else:
                    analisis_placeholder.info("✅ No se detectaron irregularidades")
                
                # Determinar el estado general
                if (temp_actual > umbral_temp_max or rpm_actual > umbral_rpm_max or 
                    rpm_actual < umbral_rpm_min or vib_actual > umbral_vib_alto):
                    status_placeholder.error(f"🚨 {status_text_display} - ¡Condición crítica!")
                elif (temp_actual > umbral_temp_min or vib_actual > umbral_vib_medio or 
                      irregularidades):
                    status_placeholder.warning(f"⚠️ {status_text_display} - Advertencia")
                else:
                    status_placeholder.success(f"✅ {status_text_display} - Normal")
                
                # Enviar alertas si se superan los umbrales
                if telegram_enabled:
                    # Alerta de temperatura alta
                    if temp_actual > umbral_temp_max and not alerta_temp_enviada:
                        mensaje = f"🚨 ALERTA: Temperatura crítica detectada\n\n• Valor actual: {temp_actual:.1f}°C\n• Umbral máximo: {umbral_temp_max}°C\n• RPM: {rpm_actual:.0f}\n• Vibración: {vib_actual:.1f} m/s²"
                        enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                        alerta_temp_enviada = True
                    
                    # Alerta de RPM alta
                    if rpm_actual > umbral_rpm_max and not alerta_rpm_alta_enviada:
                        mensaje = f"🚨 ALERTA: RPM críticas detectadas\n\n• Valor actual: {rpm_actual:.0f} RPM\n• Umbral máximo: {umbral_rpm_max} RPM\n• Temperatura: {temp_actual:.1f}°C\n• Vibración: {vib_actual:.1f} m/s²"
                        enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                        alerta_rpm_alta_enviada = True
                    
                    # Alerta de RPM baja
                    if rpm_actual < umbral_rpm_min and not alerta_rpm_baja_enviada:
                        mensaje = f"⚠️ ADVERTENCIA: RPM bajas detectadas\n\n• Valor actual: {rpm_actual:.0f} RPM\n• Umbral mínimo: {umbral_rpm_min} RPM\n• Temperatura: {temp_actual:.1f}°C\n• Vibración: {vib_actual:.1f} m/s²"
                        enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                        alerta_rpm_baja_enviada = True
                    
                    # Alerta de vibración alta
                    if vib_actual > umbral_vib_alto and not alerta_vib_alta_enviada:
                        mensaje = f"🚨 ALERTA: Vibración crítica detectada\n\n• Valor actual: {vib_actual:.1f} m/s²\n• Umbral máximo: {umbral_vib_alto} m/s²\n• Temperatura: {temp_actual:.1f}°C\n• RPM: {rpm_actual:.0f}"
                        enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                        alerta_vib_alta_enviada = True
            
            # Actualizar barra de progreso
            progress_bar.progress((i + 1) / 20)
            status_text.text(f"Leyendo datos: {i + 1}/20")
            
            time.sleep(1)  # Esperar 1 segundo entre lecturas
        
        progress_bar.empty()
        status_text.empty()
        if st.session_state.monitoreo_activo:
            st.success("✅ Ciclo de monitoreo completado")
            st.info("Presiona 'Iniciar Monitoreo' nuevamente para continuar")

with tab2:
    st.header("Análisis Histórico")
    
    # Mostrar información de ubicación y fecha
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.write(f"**📍 Ubicación:** Monterrey, México | **📅 Fecha del reporte:** {fecha_formateada}")
    
    if 'datos_reales' in st.session_state and len(st.session_state.datos_reales) > 0:
        datos = st.session_state.datos_reales
        
        # Análisis completo de irregularidades
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
            st.dataframe(datos, height=300)
        
        with col2:
            st.subheader("Estadísticas")
            col21, col22 = st.columns(2)
            with col21:
                if "Temperatura (°C)" in datos.columns:
                    st.metric("Temperatura máxima", f"{datos['Temperatura (°C)'].max():.1f}°C")
                    st.metric("Temperatura promedio", f"{datos['Temperatura (°C)'].mean():.1f}°C")
                if "RPM" in datos.columns and len(datos["RPM"]) > 0:
                    st.metric("Variación RPM", f"{(datos['RPM'].std() / datos['RPM'].mean() * 100):.1f}%" if datos['RPM'].mean() > 0 else "0%")
            with col22:
                if "RPM" in datos.columns:
                    st.metric("RPM máximo", f"{datos['RPM'].max():.0f}")
                    st.metric("RPM promedio", f"{datos['RPM'].mean():.0f}")
                    st.metric("RPM mínimo", f"{datos['RPM'].min():.0f}")
        
        # Gráfico interactivo
        st.subheader("Análisis de correlación")
        if "RPM" in datos.columns and "Temperatura (°C)" in datos.columns:
            fig_hist = px.scatter(
                datos,
                x="RPM",
                y="Temperatura (°C)",
                color="Vibración (m/s²)" if "Vibración (m/s²)" in datos.columns else None,
                title="Relación RPM vs Temperatura - Datos Reales",
                size="RPM",
                hover_data=["Hora"]
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No hay datos históricos disponibles. Inicia el monitoreo para recopilar datos.")

with tab3:
    st.header("Configuración del Sistema")
    
    st.subheader("Conexión con Arduino")
    if st.session_state.ser and st.session_state.ser.is_open:
        st.success("✅ Arduino conectado correctamente")
        st.info(f"**Puerto seleccionado:** {st.session_state.puerto_actual}")
    else:
        st.error("❌ Arduino no detectado")
        st.write("Solución de problemas:")
        st.write("1. Verifica que el Arduino esté conectado por USB")
        st.write("2. Asegúrate de que el sketch esté cargado correctamente")
        st.write("3. Reinicia el Arduino si es necesario")
        st.write("4. Verifica que el puerto COM esté disponible")
    
    st.subheader("Puertos Disponibles")
    puertos_actuales = listar_puertos_disponibles()
    if puertos_actuales:
        st.write("**Puertos detectados:**")
        for puerto in puertos_actuales:
            st.write(f"• {puerto}")
    else:
        st.warning("No se detectaron puertos seriales")
    
    st.subheader("Configuración de Telegram")
    st.write(f"**Token:** {TELEGRAM_TOKEN[:10]}...")
    st.write(f"**Chat ID:** {TELEGRAM_CHAT_ID}")
    st.write("**Estado:** ✅ Configurado correctamente" if telegram_enabled else "**Estado:** ❌ Desactivado")
    
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
st.caption("Sistema de Mantenimiento Predictivo | 📍 Monterrey, México | Alertas enviadas a Telegram | Datos en tiempo real desde Arduino")