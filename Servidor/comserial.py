import serial
import json

try:
    # Intenta abrir el puerto UART
    ser = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)

    if ser.is_open:
        print("Puerto serial abierto correctamente.")
    else:
        print("No se pudo abrir el puerto serial.")
except serial.SerialException as e:
    print("Error al abrir el puerto serial:", e)
    exit(1)  # Sale del programa si el puerto no se puede abrir

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        if line:
            data = json.loads(line)
            print("GUVA:", data["guva"])
            print("ML8511:", data["ml8511"])
            print("BH1750:", data["bh1750"])
    except Exception:
        pass  # Ignora errores de lectura o formato
