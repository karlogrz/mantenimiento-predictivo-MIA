import os
import requests
import streamlit as st
from dotenv import load_dotenv  # Paquete para leer .env

# Cargar variables de entorno
load_dotenv()  # Lee el archivo .env

# Configuración de Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Token desde .env
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Chat ID desde .env

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            st.success("✅ Alerta enviada a Telegram!")
        else:
            st.error(f"❌ Error: {response.text}")
    except Exception as e:
        st.error(f"🚨 Error de conexión: {e}")

# Ejemplo de uso en tu app
st.title("🔧 Mantenimiento Predictivo + Telegram")
if st.button("Probar Alerta"):
    send_telegram_alert(
        "🚨 <b>ALERTA DE PRUEBA</b> 🚨\n\n"
        "¡Se detectó una anomalía en el equipo!\n"
        "📊 Valor: 95°C (Límite: 80°C)\n"
        "🕒 Hora: 2024-05-20 15:45"
    )