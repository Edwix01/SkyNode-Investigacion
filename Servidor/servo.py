import time
from gpiozero import Servo

# Define el pin GPIO.
SERVO_PIN = 24


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

def mover_a_posiciones():
    """
    Mueve el servomotor a varias posiciones predefinidas.
    """
    try:
        print("Moviendo a posiciones predefinidas...")
        for valor in [-1, -0.5, 0, 0.5, 1]:
            servo.value = valor
            print(f"Valor PWM: {valor}")
            time.sleep(2)

        # Permitir ingreso manual
        while True:
            entrada = input("Ingresa un ángulo entre 0 y 180 (Enter para salir): ").strip()
            if entrada == "":
                print("Saliendo...")
                break

            try:
                angulo = int(entrada)
                valor_pwm = grados_a_value(angulo)
                servo.value = valor_pwm
                print(f"Ángulo: {angulo}° → Valor PWM: {round(valor_pwm, 2)}")
                time.sleep(2)
            except ValueError as e:
                print(f"❌ Error: {e}")

    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario.")
    finally:
        servo.detach()
        print("Servomotor detenido.")

if __name__ == "__main__":
    mover_a_posiciones()
