import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import time
import random
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Mantenimiento Predictivo",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título y descripción
st.title("🚗 Sistema de Mantenimiento Predictivo para Vehículos")
st.markdown("""
Esta aplicación simula un sistema de inteligencia artificial predictivo que analiza datos de sensores 
(temperatura y RPM) para anticipar fallas y optimizar el mantenimiento de vehículos.
""")

# Sidebar para entrada de datos
with st.sidebar:
    st.header("Configuración de Entrada")
    
    # Selector de modo
    modo = st.radio("Modo de operación:", ("Simulación en tiempo real", "Datos históricos"))
    
    if modo == "Simulación en tiempo real":
        st.subheader("Parámetros de Simulación")
        temp_min = st.slider("Temperatura mínima (°C)", 70, 90, 75)
        temp_max = st.slider("Temperatura máxima (°C)", 90, 120, 95)
        rpm_min = st.slider("RPM mínima", 1000, 2000, 1200)
        rpm_max = st.slider("RPM máxima", 2000, 5000, 3000)
        frecuencia = st.slider("Frecuencia de medición (segundos)", 1, 10, 2)
        
        iniciar_simulacion = st.button("Iniciar Simulación")
        detener_simulacion = st.button("Detener Simulación")
        
    else:
        st.subheader("Carga de Datos Históricos")
        archivo = st.file_uploader("Subir archivo CSV", type=["csv"])
        if archivo:
            datos_historicos = pd.read_csv(archivo)
            st.success("Datos cargados correctamente")

# Funciones de utilidad
def generar_datos_sinteticos(n=1000):
    """Genera datos sintéticos para la demostración"""
    np.random.seed(42)
    
    # Generar datos normales
    temp_normal = np.random.normal(85, 5, n)
    rpm_normal = np.random.normal(2500, 500, n)
    estado_normal = ["Normal"] * n
    
    # Generar datos de falla (temperatura alta)
    temp_alta = np.random.normal(105, 7, n//2)
    rpm_alta = np.random.normal(2800, 600, n//2)
    estado_alta = ["Falla por temperatura"] * (n//2)
    
    # Generar datos de falla (RPM alta)
    temp_rpm = np.random.normal(90, 6, n//2)
    rpm_alta2 = np.random.normal(4000, 800, n//2)
    estado_rpm = ["Falla por RPM"] * (n//2)
    
    # Combinar todos los datos
    temperaturas = np.concatenate([temp_normal, temp_alta, temp_rpm])
    rpm = np.concatenate([rpm_normal, rpm_alta, rpm_alta2])
    estados = np.concatenate([estado_normal, estado_alta, estado_rpm])
    
    # Crear DataFrame
    fechas = pd.date_range(start='2023-01-01', periods=len(temperaturas), freq='H')
    df = pd.DataFrame({
        'fecha': fechas,
        'temperatura': temperaturas,
        'rpm': rpm,
        'estado': estados
    })
    
    return df

def predecir_falla(temperatura, rpm):
    """Función simple para predecir fallas basada en reglas"""
    if temperatura > 100 and rpm > 3500:
        return "Alerta Crítica: Falla inminente por sobrecalentamiento y alto RPM"
    elif temperatura > 100:
        return "Alerta: Temperatura crítica"
    elif rpm > 3500:
        return "Alerta: RPM crítico"
    elif temperatura > 95:
        return "Advertencia: Temperatura elevada"
    elif rpm > 3000:
        return "Advertencia: RPM elevado"
    else:
        return "Normal"

def simular_falla(temperatura, rpm):
    """Simula posibles fallas en piezas basado en temperatura y RPM"""
    fallas = []
    
    if temperatura > 100:
        fallas.append(("Sistema de refrigeración", 0.85))
        fallas.append(("Junta de culata", 0.75))
    
    if rpm > 3500:
        fallas.append(("Embrague", 0.8))
        fallas.append(("Transmisión", 0.7))
    
    if temperatura > 100 and rpm > 3500:
        fallas.append(("Motor completo", 0.9))
        fallas.append(("Sistema de lubricación", 0.8))
    
    # Ordenar por probabilidad descendente
    fallas.sort(key=lambda x: x[1], reverse=True)
    
    return fallas

# Cargar o generar datos
if 'datos' not in st.session_state:
    st.session_state.datos = generar_datos_sinteticos()

if 'mediciones' not in st.session_state:
    st.session_state.mediciones = []

if 'simulando' not in st.session_state:
    st.session_state.simulando = False

# Lógica para la simulación en tiempo real
if modo == "Simulación en tiempo real":
    if iniciar_simulacion:
        st.session_state.simulando = True
    
    if detener_simulacion:
        st.session_state.simulando = False
    
    if st.session_state.simulando:
        st.info("Simulación en curso...")
        
        # Generar nueva medición
        nueva_temperatura = random.uniform(temp_min, temp_max)
        nueva_rpm = random.uniform(rpm_min, rpm_max)
        estado = predecir_falla(nueva_temperatura, nueva_rpm)
        timestamp = datetime.now()
        
        # Guardar medición
        st.session_state.mediciones.append({
            'timestamp': timestamp,
            'temperatura': nueva_temperatura,
            'rpm': nueva_rpm,
            'estado': estado
        })
        
        # Mostrar alerta si es necesario
        if "Alerta" in estado:
            st.error(f"🚨 {estado} - {timestamp.strftime('%H:%M:%S')}")
        elif "Advertencia" in estado:
            st.warning(f"⚠️ {estado} - {timestamp.strftime('%H:%M:%S')}")
        else:
            st.success(f"✅ {estado} - {timestamp.strftime('%H:%M:%S')}")
        
        # Esperar antes de la próxima medición
        time.sleep(frecuencia)
        st.rerun()

# Mostrar datos y análisis
st.header("Análisis de Datos")

# Pestañas para organizar la visualización
tab1, tab2, tab3, tab4 = st.tabs([
    "Distribución", 
    "Concordancia", 
    "Registro de Mediciones", 
    "Simulador de Fallas"
])

with tab1:
    st.subheader("Distribución de Temperatura y RPM")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_temp = px.histogram(
            st.session_state.datos, 
            x='temperatura', 
            color='estado',
            title='Distribución de Temperatura',
            nbins=30
        )
        st.plotly_chart(fig_temp, use_container_width=True)
    
    with col2:
        fig_rpm = px.histogram(
            st.session_state.datos, 
            x='rpm', 
            color='estado',
            title='Distribución de RPM',
            nbins=30
        )
        st.plotly_chart(fig_rpm, use_container_width=True)
    
    # Gráfico de dispersión
    fig_scatter = px.scatter(
        st.session_state.datos,
        x='temperatura',
        y='rpm',
        color='estado',
        title='Relación entre Temperatura y RPM'
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    st.subheader("Gráfico de Concordancia")
    
    # Preparar datos para el gráfico de concordancia
    datos_concordancia = st.session_state.datos.copy()
    datos_concordancia['fecha_num'] = pd.to_datetime(datos_concordancia['fecha']).astype(int) / 10**9
    
    fig_concordancia = go.Figure()
    
    # Agregar trazas para temperatura
    fig_concordancia.add_trace(go.Scatter(
        x=datos_concordancia['fecha'],
        y=datos_concordancia['temperatura'],
        mode='lines',
        name='Temperatura',
        yaxis='y1'
    ))
    
    # Agregar trazas para RPM
    fig_concordancia.add_trace(go.Scatter(
        x=datos_concordancia['fecha'],
        y=datos_concordancia['rpm'],
        mode='lines',
        name='RPM',
        yaxis='y2'
    ))
    
    # Configurar diseño del gráfico
    fig_concordancia.update_layout(
        title='Concordancia entre Temperatura y RPM a lo largo del tiempo',
        xaxis=dict(title='Fecha'),
        yaxis=dict(title='Temperatura (°C)', side='left'),
        yaxis2=dict(title='RPM', side='right', overlaying='y'),
        legend=dict(x=0, y=1.1, orientation='h')
    )
    
    st.plotly_chart(fig_concordancia, use_container_width=True)
    
    # Mostrar correlación
    correlacion = np.corrcoef(datos_concordancia['temperatura'], datos_concordancia['rpm'])[0, 1]
    st.metric("Correlación entre Temperatura y RPM", f"{correlacion:.2f}")

with tab3:
    st.subheader("Registro de Mediciones")
    
    if st.session_state.mediciones:
        # Crear DataFrame con las mediciones
        df_mediciones = pd.DataFrame(st.session_state.mediciones)
        
        # Mostrar tabla
        st.dataframe(df_mediciones.sort_values('timestamp', ascending=False))
        
        # Opción para descargar datos
        csv = df_mediciones.to_csv(index=False)
        st.download_button(
            label="Descargar registro como CSV",
            data=csv,
            file_name="registro_mantenimiento.csv",
            mime="text/csv"
        )
    else:
        st.info("No hay mediciones registradas. Inicie la simulación para generar datos.")

with tab4:
    st.subheader("Simulador de Fallas en Piezas")
    
    # Selectores para parámetros de simulación
    col1, col2 = st.columns(2)
    
    with col1:
        temp_sim = st.slider("Temperatura para simulación (°C)", 70, 120, 85)
    
    with col2:
        rpm_sim = st.slider("RPM para simulación", 1000, 5000, 2500)
    
    # Simular fallas
    fallas_simuladas = simular_falla(temp_sim, rpm_sim)
    
    if fallas_simuladas:
        st.warning("⚠️ Se detectaron posibles fallas en las siguientes piezas:")
        
        for pieza, probabilidad in fallas_simuladas:
            # Crear una barra de progreso para la probabilidad
            st.write(f"{pieza}: {probabilidad*100:.1f}% de probabilidad")
            st.progress(probabilidad)
    else:
        st.success("✅ No se detectaron fallas potenciales con estos parámetros.")
    
    # Mostrar recomendaciones
    st.subheader("Recomendaciones de Mantenimiento")
    
    if temp_sim > 100:
        st.info("""
        **Para temperatura alta:**
        - Verificar nivel de refrigerante
        - Revisar funcionamiento del ventilador
        - Limpiar radiador y conductos de refrigeración
        """)
    
    if rpm_sim > 3500:
        st.info("""
        **Para RPM alto:**
        - Verificar sistema de embrague
        - Revisar cambio de marchas
        - Realizar alineación y balanceo
        """)
    
    if temp_sim <= 95 and rpm_sim <= 3000:
        st.info("""
        **Mantenimiento preventivo general:**
        - Cambio de aceite y filtros
        - Revisión de frenos
        - Inspección de neumáticos
        """)

# Pie de página
st.markdown("---")
st.markdown("""
### Acerca de este sistema
Este sistema de mantenimiento predictivo utiliza inteligencia artificial para analizar datos de sensores 
y anticipar posibles fallas en vehículos. Los datos mostrados son simulados para demostración.
""")