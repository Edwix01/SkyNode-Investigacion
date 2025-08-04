import time
from gpiozero import Servo

# Define el pin GPIO.
SERVO_PIN = 16

# Inicializa el objeto Servo con pulsos adecuados (ajusta si tu servo lo requiere)
servo = Servo(SERVO_PIN, min_pulse_width=0.0005, max_pulse_width=0.0025)

def grados_a_value(grados):
    """
    Convierte un ángulo de 0° a 180° al rango -1.0 a 1.0 de gpiozero.
    """
    if 0 <= grados <= 180:
        return (grados / 90.0) - 1.0
    else:
        raise ValueError("El ángulo debe estar entre 0 y 180 grados.")

def mover_a_posiciones(estado):
    """
    Mueve el servomotor a varias posiciones predefinidas.
    """
    try:

        try:
            if estado:
                valor_pwm = grados_a_value(180)
                servo.value = valor_pwm
                print(f"Cerrando Cubierta")
                time.sleep(2)
            else:
                valor_pwm = grados_a_value(0)
                servo.value = valor_pwm
                print(f"Cubierta Abierta")
                time.sleep(2)

        except ValueError as e:
            print(f"❌ Error: {e}")

    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario.")
    finally:
        servo.detach()
        print("Servomotor detenido.")

