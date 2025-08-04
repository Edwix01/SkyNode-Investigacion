# mqtt_client.py
import paho.mqtt.client as mqtt
import time
import threading
from database import obtener_valor_configuracion;

# Datos de conexión
mqtt_broker = "192.168.18.5"  # IP de la Raspberry Pi o servidor MQTT
mqtt_port = 1883
mqtt_subscribe_topic = "esp32/respuesta"  # Tópico para recibir la respuesta
mqtt_publish_topic = "raspberry/solicitar_datos"  # Tópico para enviar la solicitud

# Función que se ejecuta cuando el cliente se conecta al servidor MQTT
def on_connect(client, userdata, flags, rc):
    print(f"Conectado con el código {rc}")
    client.subscribe(mqtt_subscribe_topic)  # Suscribirse al tópico de respuesta

# Función que se ejecuta cuando se recibe un mensaje en el tópico suscrito
def on_message(client, userdata, msg):
    print(f"Mensaje recibido: {msg.payload.decode()}")

# Crear el cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Conectar al broker MQTT
def conectar_cliente():
    try:
        client.connect(mqtt_broker, mqtt_port, 60)
    except Exception as e:
        print(f"Error al conectar al broker MQTT: {e}")

# Función para enviar solicitud cada 15 segundos
def enviar_solicitudes():
    while True:
        try:
            print("Enviando solicitud de datos al ESP32...")
            client.publish(mqtt_publish_topic, "solicitar_datos")  # Enviar la solicitud
        except Exception as e:
            print(f"Error al enviar solicitud: {e}")
        
        frecuencia_str = obtener_valor_configuracion("frecuencia_peticion")
        frecuencia = int(frecuencia_str)
        time.sleep(frecuencia)  # Esperar 50 segundos antes de enviar la siguiente solicitud

# Iniciar la conexión MQTT en un hilo separado
def iniciar_mqtt():
    conectar_cliente()

    # Iniciar el envío de solicitudes en un hilo aparte para no bloquear la recepción de mensajes
    solicitudes_thread = threading.Thread(target=enviar_solicitudes)
    solicitudes_thread.daemon = True
    solicitudes_thread.start()

    # Mantener la conexión y recibir mensajes
    client.loop_forever()
