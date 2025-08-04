import os
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from mqttconec import iniciar_mqtt  # Importa la función que maneja MQTT
import threading


# Inicializar FastAPI
app = FastAPI()

# Montar carpetas estáticas
app.mount("/imagenes", StaticFiles(directory="imagenes"), name="imagenes")

# Plantillas Jinja2
templates = Jinja2Templates(directory="templates")

# Crear carpetas necesarias
os.makedirs("imagenes", exist_ok=True)
os.makedirs("datos", exist_ok=True)

from routes import endpoints

app.include_router(endpoints.router)
# Ejecutar el cliente MQTT en un hilo
def run_mqtt():
    iniciar_mqtt()

threading.Thread(target=run_mqtt, daemon=True).start()