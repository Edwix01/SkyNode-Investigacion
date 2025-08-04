#!/bin/bash

# Archivo donde se guardarán los registros
OUTPUT_FILE="/home/pv1/Documents/Server/temperatura_log.txt"

# Intervalo en segundos
INTERVALO=30

echo "Registro de temperatura iniciado. Guardando en $OUTPUT_FILE"
echo "Fecha y hora | Temperatura (°C)" >> "$OUTPUT_FILE"
echo "-------------------------------" >> "$OUTPUT_FILE"

while true
do
    # Obtener la fecha y hora actual
    FECHA=$(date '+%Y-%m-%d %H:%M:%S')

    # Obtener la temperatura y convertirla a °C
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    TEMP_C=$(echo "scale=1; $TEMP / 1000" | bc)

    # Guardar en archivo
    echo "$FECHA | $TEMP_C" >> "$OUTPUT_FILE"

    # Esperar 30 segundos
    sleep $INTERVALO
done

