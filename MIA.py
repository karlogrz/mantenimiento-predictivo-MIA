import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
from streamlit_lottie import st_lottie
import json
import requests
from datetime import datetime
import pytz

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

def obtener_fecha_hora_mty():
    """Obtiene la fecha y hora actual de Monterrey, México"""
    ahora = datetime.now(ZONA_HORARIA)
    return ahora.strftime("%Y-%m-%d %H:%M:%S"), ahora.strftime("%A, %d de %B de %Y"), ahora.strftime("%H:%M:%S")

def analizar_irregularidades_rpm(datos_rpm):
    """Analiza irregularidades en las RPM y sugiere fallos probables"""
    irregularidades = []
    fallos_probables = []
    
    # Calcular estadísticas
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

def predecir_fallo(temp_actual, rpm_actual, historial_rpm):
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
    
    # Eliminar duplicados y priorizar
    fallos_probables = list(set(fallos_probables))
    
    # Priorizar fallos basados en severidad
    if "Sobrecarga del motor" in fallos_probables:
        fallo_principal = "Sobrecarga del motor"
    elif "Fallo de refrigeración" in fallos_probables:
        fallo_principal = "Fallo de refrigeración"
    elif "Bujías desgastadas" in fallos_probables:
        fallo_principal = "Bujías desgastadas"
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
    # Datos más realistas con posibles irregularidades
    rpm = np.random.normal(2500, 200, 24)
    # Añadir algunas irregularidades
    rpm[5:8] += np.random.normal(400, 100, 3)  # Pico de RPM
    rpm[15:18] -= np.random.normal(300, 80, 3)  # Caída de RPM
    
    datos = pd.DataFrame({
        "Hora": horas,
        "RPM": rpm,
        "Temperatura (°C)": np.random.normal(85, 12, 24)
    })
    return datos

# ---- Sidebar (Controles de usuario) ----
st.sidebar.header("🔧 Panel de Control")

# Mostrar hora actual de Monterrey
fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
st.sidebar.info(f"📍 Monterrey, México\n📅 {fecha_formateada}\n🕒 {hora_actual}")

# Botón de Iniciar Monitoreo
st.sidebar.header("🚀 Control de Monitoreo")
if 'monitoreo_activo' not in st.session_state:
    st.session_state.monitoreo_activo = False

if st.sidebar.button("▶️ Iniciar", type="primary", use_container_width=True):
    st.session_state.monitoreo_activo = True
    st.sidebar.success("✅ Monitoreo iniciado")

if st.session_state.monitoreo_activo:
    st.sidebar.info("🔴 Monitoreo en curso...")
    if st.sidebar.button("⏹️ Detener", use_container_width=True):
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

# Selector de variables a visualizar
st.sidebar.subheader("📊 Visualización")
variables = st.sidebar.multiselect(
    "Variables a visualizar",
    ["RPM", "Temperatura (°C)"],
    default=["Temperatura (°C)", "RPM"]
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
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📅 Histórico", "⚙️ Simulador"])

with tab1:
    st.header("Monitoreo en Tiempo Real")
    
    # Mostrar hora actual
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.write(f"**📍 Ubicación:** Monterrey, México | **📅 Fecha:** {fecha_formateada} | **🕒 Hora:** {hora_actual}")
    
    if not st.session_state.monitoreo_activo:
        st.warning("⏸️ El monitoreo está detenido. Presiona 'Iniciar' en el panel de control para comenzar.")
        st.info("💡 Configure los umbrales y visualización antes de iniciar el monitoreo.")
    else:
        # Gráfico dinámico (simulación de streaming)
        chart_placeholder = st.empty()
        status_placeholder = st.empty()
        analisis_placeholder = st.empty()
        datos = generar_datos_sinteticos()
        
        # Variables para controlar el envío de alertas
        alerta_temp_enviada = False
        alerta_rpm_alta_enviada = False
        alerta_rpm_baja_enviada = False
        historial_rpm = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(len(datos)):
            if not st.session_state.monitoreo_activo:
                st.warning("Monitoreo detenido por el usuario")
                break
                
            subset = datos.iloc[:i+1]
            fig = px.line(subset, x="Hora", y=variables, title="Tendencias en Tiempo Real - Monterrey, México")
            chart_placeholder.plotly_chart(fig, use_container_width=True)
            
            # Actualizar barra de progreso
            progress = (i + 1) / len(datos)
            progress_bar.progress(progress)
            status_text.text(f"Procesando datos: {i + 1}/{len(datos)}")
            
            # Obtener fecha y hora actual para Monterrey
            fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
            
            # Verificar alertas en cada iteración
            temp_actual = subset["Temperatura (°C)"].iloc[-1]
            rpm_actual = subset["RPM"].iloc[-1]
            hora_simulada = subset["Hora"].iloc[-1]
            
            # Actualizar historial de RPM para análisis
            historial_rpm.append(rpm_actual)
            if len(historial_rpm) > 10:  # Mantener solo últimas 10 mediciones
                historial_rpm = historial_rpm[-10:]
            
            # Analizar irregularidades
            irregularidades, fallos_probables, fallo_principal = predecir_fallo(temp_actual, rpm_actual, historial_rpm)
            
            # Mostrar estado actual
            status_text_display = f"**Hora: {hora_simulada}:00** | Temperatura: {temp_actual:.1f}°C | RPM: {rpm_actual:.0f}"
            
            # Mostrar análisis de irregularidades
            if irregularidades:
                analisis_text = "🔍 **Irregularidades detectadas:**\n"
                for irregularidad in irregularidades:
                    analisis_text += f"• {irregularidad}\n"
                analisis_text += f"⚠️ **Fallo probable:** {fallo_principal}"
                analisis_placeholder.warning(analisis_text)
            else:
                analisis_placeholder.info("✅ No se detectaron irregularidades en RPM")
            
            # Determinar el estado general
            if temp_actual > umbral_temp_max or rpm_actual > umbral_rpm_max or rpm_actual < umbral_rpm_min:
                status_placeholder.error(f"🚨 {status_text_display} - ¡Condición crítica!")
            elif temp_actual > umbral_temp_min or irregularidades:
                status_placeholder.warning(f"⚠️ {status_text_display} - Advertencia")
            else:
                status_placeholder.success(f"✅ {status_text_display} - Normal")
            
            # Enviar alertas si se superan los umbrales
            if telegram_enabled:
                # Alerta de temperatura alta
                if temp_actual > umbral_temp_max and not alerta_temp_enviada:
                    mensaje = f"🚨 ALERTA: Temperatura crítica detectada\n\n• Valor actual: {temp_actual:.1f}°C\n• Umbral máximo: {umbral_temp_max}°C\n• Hora simulada: {hora_simulada}:00\n• RPM: {rpm_actual:.0f}"
                    enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                    alerta_temp_enviada = True
                
                # Alerta de RPM alta
                if rpm_actual > umbral_rpm_max and not alerta_rpm_alta_enviada:
                    mensaje = f"🚨 ALERTA: RPM críticas detectadas\n\n• Valor actual: {rpm_actual:.0f} RPM\n• Umbral máximo: {umbral_rpm_max} RPM\n• Hora simulada: {hora_simulada}:00\n• Temperatura: {temp_actual:.1f}°C"
                    enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                    alerta_rpm_alta_enviada = True
                
                # Alerta de RPM baja
                if rpm_actual < umbral_rpm_min and not alerta_rpm_baja_enviada:
                    mensaje = f"⚠️ ADVERTENCIA: RPM bajas detectadas\n\n• Valor actual: {rpm_actual:.0f} RPM\n• Umbral mínimo: {umbral_rpm_min} RPM\n• Hora simulada: {hora_simulada}:00\n• Temperatura: {temp_actual:.1f}°C"
                    enviar_alerta_telegram(mensaje, irregularidades, fallo_principal)
                    alerta_rpm_baja_enviada = True
            
            time.sleep(0.5)  # Velocidad de actualización
        
        progress_bar.empty()
        status_text.empty()
        if st.session_state.monitoreo_activo:
            st.success("✅ Monitoreo completado")

with tab2:
    st.header("Análisis Histórico")
    
    # Mostrar información de ubicación y fecha
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.write(f"**📍 Ubicación:** Monterrey, México | **📅 Fecha del reporte:** {fecha_formateada}")
    
    datos = generar_datos_sinteticos()
    
    # Análisis completo de irregularidades
    st.subheader("🔍 Análisis de Irregularidades en RPM")
    irregularidades, fallos_probables = analizar_irregularidades_rpm(datos["RPM"].values)
    
    if irregularidades:
        st.warning("**Irregularidades detectadas:**")
        for irregularidad in irregularidades:
            st.write(f"• {irregularidad}")
        
        st.error("**Fallos probables:**")
        for fallo in fallos_probables:
            st.write(f"• {fallo}")
    else:
        st.success("✅ No se detectaron irregularidades significativas en las RPM")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Datos completos")
        st.dataframe(datos, height=300)
    
    with col2:
        st.subheader("Estadísticas")
        col21, col22 = st.columns(2)
        with col21:
            st.metric("Temperatura máxima", f"{datos['Temperatura (°C)'].max():.1f}°C")
            st.metric("Temperatura promedio", f"{datos['Temperatura (°C)'].mean():.1f}°C")
            st.metric("Variación RPM", f"{(datos['RPM'].std() / datos['RPM'].mean() * 100):.1f}%")
        with col22:
            st.metric("RPM máximo", f"{datos['RPM'].max():.0f}")
            st.metric("RPM promedio", f"{datos['RPM'].mean():.0f}")
            st.metric("RPM mínimo", f"{datos['RPM'].min():.0f}")
    
    # Gráfico interactivo
    st.subheader("Análisis de correlación")
    fig_hist = px.scatter(
        datos,
        x="RPM",
        y="Temperatura (°C)",
        color="Hora",
        title="Relación RPM vs Temperatura - Monterrey, México",
        size="RPM",
        hover_data=["Hora"]
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with tab3:
    st.header("Simulador de Fallos")
    
    # Mostrar hora actual
    fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
    st.write(f"**📍 Ubicación:** Monterrey, México | **🕒 Hora de simulación:** {hora_actual}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Selector de fallos
        fallo = st.selectbox("Selecciona un fallo para simular:", 
                           ["Bujías", "Sobrecarga", "Fallo de refrigeración", "Filtro obstruido", "Problema de encendido", "Inyectores defectuosos"])
        
        # Parámetros de simulación
        temp_simulacion = st.slider("Temperatura simulada (°C)", 50, 150, 110)
        rpm_simulacion = st.slider("RPM simuladas", 1000, 4000, 2800)
        variacion_rpm = st.slider("Variación de RPM (%)", 0, 50, 20)
        
        if st.button("🔍 Simular fallo", type="primary"):
            fecha_completa, fecha_formateada, hora_actual = obtener_fecha_hora_mty()
            
            # Simular irregularidades basadas en el fallo seleccionado
            if fallo == "Bujías":
                sintomas = "RPM inestables, aumento de temperatura"
                irregularidades = [f"Alta variación en RPM ({variacion_rpm}%)", "Chispa intermitente detectada"]
                fallo_probable = "Bujías desgastadas"
                st.error(f"🚨 {sintomas}")
                
            elif fallo == "Fallo de refrigeración":
                sintomas = "Temperatura elevada persistente, ventilador no funciona"
                irregularidades = ["Temperatura críticamente alta", "RPM estables pero temperatura elevada"]
                fallo_probable = "Fallo de refrigeración"
                st.warning(f"⚠️ {sintomas}")
                
            elif fallo == "Filtro obstruido":
                sintomas = "RPM bajas, temperatura variable"
                irregularidades = ["RPM consistently bajas", "Pérdida de potencia"]
                fallo_probable = "Filtro de aire obstruido"
                st.warning(f"⚠️ {sintomas}")
            
            elif fallo == "Problema de encendido":
                sintomas = "RPM irregulares, dificultad al arrancar"
                irregularidades = ["Patrón irregular en RPM", "Fallos de encendido detectados"]
                fallo_probable = "Bobinas de encendido defectuosas"
                st.error(f"🚨 {sintomas}")
            
            elif fallo == "Inyectores defectuosos":
                sintomas = "RPM fluctuantes, consumo excesivo de combustible"
                irregularidades = ["RPM inestables", "Rendimiento pobre del motor"]
                fallo_probable = "Inyectores de combustible defectuosos"
                st.error(f"🚨 {sintomas}")
                
            else:  # Sobrecarga
                sintomas = "Temperatura > 110°C, pérdida de potencia"
                irregularidades = ["Temperatura críticamente alta", "RPM forzadas"]
                fallo_probable = "Sobrecarga del motor"
                st.error(f"🚨 {sintomas}")
            
            if telegram_enabled:
                mensaje = f"🔧 SIMULACIÓN: {fallo}\n• Síntomas: {sintomas}\n• Temperatura: {temp_simulacion}°C\n• RPM: {rpm_simulacion}"
                enviar_alerta_telegram(mensaje, irregularidades, fallo_probable)
    
    with col2:
        st.subheader("Información del fallo")
        if fallo == "Bujías":
            st.info("""
            **Fallo en bujías:**
            - Causa: Desgaste normal o contaminación
            - Síntomas: RPM inestables, aumento de temperatura
            - Variación típica de RPM: 15-25%
            - Solución: Reemplazar bujías
            """)
        elif fallo == "Fallo de refrigeración":
            st.info("""
            **Fallo en sistema de refrigeración:**
            - Causa: Fuga de refrigerante o ventilador dañado
            - Síntomas: Temperatura elevada persistente
            - Temperatura típica: >100°C
            - Solución: Reparar fugas, revisar ventilador
            """)
        elif fallo == "Filtro obstruido":
            st.info("""
            **Filtro de aire obstruido:**
            - Causa: Acumulación de suciedad
            - Síntomas: RPM bajas, rendimiento reducido
            - RPM típicas: <1800
            - Solución: Reemplazar filtro de aire
            """)
        elif fallo == "Problema de encendido":
            st.info("""
            **Problema de encendido:**
            - Causa: Bobinas o cables de bujía defectuosos
            - Síntomas: RPM irregulares, dificultad al arrancar
            - Variación típica: >20%
            - Solución: Revisar sistema de encendido
            """)
        elif fallo == "Inyectores defectuosos":
            st.info("""
            **Inyectores defectuosos:**
            - Causa: Obstrucción o desgaste de inyectores
            - Síntomas: RPM fluctuantes, consumo excesivo
            - Variación típica: 15-30%
            - Solución: Limpiar o reemplazar inyectores
            """)
        else:
            st.info("""
            **Sobrecarga del motor:**
            - Causa: Exceso de carga o conducción agresiva
            - Síntomas: Temperatura elevada, pérdida de potencia
            - Temperatura típica: >110°C
            - Solución: Reducir carga, revisar aceite
            """)

# ---- Alertas en Sidebar ----
st.sidebar.header("🚨 Alertas Activas")
if 'monitoreo_activo' in st.session_state and st.session_state.monitoreo_activo:
    datos = generar_datos_sinteticos()
    temp_maxima = datos["Temperatura (°C)"].max()
    rpm_maxima = datos["RPM"].max()
    rpm_minima = datos["RPM"].min()

    if temp_maxima > umbral_temp_max:
        st.sidebar.error(f"🌡️ Temp crítica: {temp_maxima}°C > {umbral_temp_max}°C")
    elif temp_maxima > umbral_temp_min:
        st.sidebar.warning(f"🌡️ Temp alta: {temp_maxima}°C")

    if rpm_maxima > umbral_rpm_max:
        st.sidebar.error(f"⚙️ RPM críticas: {rpm_maxima} > {umbral_rpm_max}")
    if rpm_minima < umbral_rpm_min:
        st.sidebar.error(f"⚙️ RPM bajas: {rpm_minima} < {umbral_rpm_min}")

    # Análisis de irregularidades en sidebar
    irregularidades, _ = analizar_irregularidades_rpm(datos["RPM"].values)
    if irregularidades:
        st.sidebar.warning("⚠️ Irregularidades en RPM detectadas")

    if temp_maxima <= umbral_temp_min and rpm_maxima <= umbral_rpm_max and rpm_minima >= umbral_rpm_min and not irregularidades:
        st.sidebar.success("✅ Todos los parámetros dentro de rangos normales")
else:
    st.sidebar.info("⏸️ Monitoreo detenido - Sin datos activos")

# ---- Botón de descarga ----
st.sidebar.download_button(
    "📥 Descargar Datos",
    generar_datos_sinteticos().to_csv(),
    file_name="datos_motor.csv",
    mime="text/csv"
)

# ---- Información de conexión ----
with st.sidebar.expander("🔗 Estado de conexión"):
    st.write(f"**Token:** `{TELEGRAM_TOKEN[:10]}...`")
    st.write(f"**Chat ID:** `{TELEGRAM_CHAT_ID}`")
    st.write("**Ubicación:** Monterrey, México")
    st.write("**Zona horaria:** America/Monterrey")
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
st.caption("Sistema de Mantenimiento Predictivo | 📍 Monterrey, México | Alertas enviadas a Telegram")