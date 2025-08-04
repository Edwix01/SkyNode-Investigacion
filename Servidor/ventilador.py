from gpiozero import LED
from signal import pause

# Crear objeto LED en GPIO 16
ventilador = LED(23)

def ventilador_state(estado):
    try:
        if estado == "on":
            ventilador.on()
            print("Ventilador encendido")
        elif estado == "off":
            ventilador.off()
            print("Ventilador apagado")
        else:
            print("No se reconoce el estado del ventilador")
    except KeyboardInterrupt:
        print("Interrupción del usuario")

