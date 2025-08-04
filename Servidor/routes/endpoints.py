import os
from fastapi import  Request,HTTPException,Form,BackgroundTasks
from fastapi.responses import  FileResponse, HTMLResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime
import mariadb
import csv
from io import StringIO
from CamaraConfigurable import CamaraPi  # Importar la clase de captura
import zipfile, os, json
from typing import List
from collections import defaultdict
from main import templates  # Importa la instancia de Jinja2Templates desde main.py
from database import get_data_from_db, SensorDataGraficos, obtener_conexion
from fastapi import APIRouter
from io import BytesIO
from cubierta import mover_a_posiciones
from ventilador import ventilador_state


IMAGE_DIR = "exported_images"

router = APIRouter()
# Conexión a la base de datos
def capturar_y_guardar_imagen(nombre_imagen):
    # Leer configuraciones desde la base de datos
    conn = obtener_conexion()
    cur = conn.cursor()
    parametros = [
        "AnalogueGain", "ExposureTime", "AeEnable", "AwbEnable",
        "Brightness", "Contrast", "Saturation", "Sharpness"
    ]
    
    config = {}
    for nombre in parametros:
        cur.execute("SELECT valor FROM configuraciones WHERE nombre = ?", (nombre,))
        resultado = cur.fetchone()
        if resultado is not None:
            valor = resultado[0]
            if nombre in ["AeEnable", "AwbEnable"]:
                config[nombre] = bool(int(valor))  # Convertir a booleano
            elif nombre in ["Contrast", "ExposureTime"]:
                config[nombre] = int(valor)  # Convertir a entero
            else:
                config[nombre] = float(valor)  # Convertir a float
        else:
            # Valores por defecto
            config[nombre] = {
                "AnalogueGain": 1.0,
                "ExposureTime": 10000,
                "Brightness": 0.5,
                "Contrast": 1,
                "Saturation": 1.0,
                "Sharpness": 1.0,
                "AeEnable": False,
                "AwbEnable": True
            }.get(nombre)

    cur.close()
    conn.close()

    print(f"Configurando cámara con: {config}")

    cam = CamaraPi(
    )

    #Usar para configurar la cámara 
        # gain=float(config["AnalogueGain"]),
        # exposure_time=int(config["ExposureTime"]),
        # ae_mode=bool(config["AeEnable"]),
        # aw_mode=bool(config["AwbEnable"]),
        # brightness=float(config["Brightness"]),
        # contrast=int(config["Contrast"]),
        # saturation=float(config["Saturation"]),
        # sharpness=float(config["Sharpness"])

    cam.capture_raw(nombre_imagen)
    cam.close()

def get_raspberry_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_str = f.read()  # Lee el valor, por ejemplo "42000"
        return float(temp_str) / 1000.0  # Convierte a 42.0 °C
    except Exception:
        return None
    
class SensorData(BaseModel):
    ml8511: int
    ml8511_2: int
    visible: int
    visible_2: int
    humedad: float
    temp_dht: float
    temp_bmp: float
    presion_bmp: float
    lat: float
    lng: float
    satelites: int
    altitud: float
    fecha: str
    hora: str
    temp_max_c: float
    temp_max_f: float

@router.get("/sensor_data/{time_range}")
async def sensor_data(time_range: str, request: Request):
    start = request.query_params.get("start")
    end = request.query_params.get("end")
    return get_data_from_db(time_range, start, end)

# 🏠 Ruta principal
@router.get("/", response_class=HTMLResponse)
async def inicio(request: Request):
    return templates.TemplateResponse("inicio.html", {"request": request})
# 📈 Dashboard
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM registros ORDER BY timestamp DESC LIMIT 1")
        ultimo = cursor.fetchone()
        cursor.close()
        conn.close()
        return templates.TemplateResponse("sensores.html", {"request": request, "datos": ultimo, "resultados": None})
    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en DB: {e}")

@router.get("/consulta", response_class=HTMLResponse)
async def consulta(
    request: Request,
    desde: str = None,
    hasta: str = None,
    cantidad: int = 10,
    hora_inicio: str = None,
    hora_final: str = None,
    rango_ml8511: str = None,
    rango_visible: str = None,
    sin_limite: int = 0
):
    columnas_validas = [
        "ml8511", "ml8511_2", "visible", "visible_2", "humedad", "temp_dht", "temp_bmp",
        "presion_bmp", "lat", "lng", "satelites", "altitud", "temp_max_c", "temp_max_f"
    ]  # Agrega todos los sensores válidos aquí

    # Obtener los sensores seleccionados
    sensores = request.query_params.getlist("sensores")
    sensores = [s for s in sensores if s in columnas_validas]
    if not sensores:
        sensores = ["ml8511"]

    conn = obtener_conexion()
    cursor = conn.cursor(dictionary=True)

    # Obtener el último registro
    cursor.execute("SELECT * FROM registros ORDER BY timestamp DESC LIMIT 1")
    ultimo = cursor.fetchone()

    # Armar la consulta dinámica
    query = "SELECT timestamp, " + ", ".join(sensores) + ", imagen FROM registros WHERE 1=1"
    params = []

    # Filtro por fecha
    if desde:
        query += " AND timestamp >= ?"
        params.append(desde + " 00:00:00")
    if hasta:
        query += " AND timestamp <= ?"
        params.append(hasta + " 23:59:59")

    # Filtro por hora
    if hora_inicio and hora_final:
        query += " AND TIME(timestamp) BETWEEN ? AND ?"
        params.append(hora_inicio)
        params.append(hora_final)

    # Filtro por rangos de sensores (puedes agregar más filtros aquí si lo necesitas)
    if rango_ml8511:
        partes = rango_ml8511.split("-")
        if len(partes) == 2:
            query += " AND ml8511 BETWEEN ? AND ?"
            params.append(float(partes[0]))
            params.append(float(partes[1]))

    if rango_visible:
        partes = rango_visible.split("-")
        if len(partes) == 2:
            query += " AND visible BETWEEN ? AND ?"
            params.append(float(partes[0]))
            params.append(float(partes[1]))

    # Orden y límite
    query += " ORDER BY timestamp DESC"
    if not sin_limite:
        query += " LIMIT ?"
        params.append(cantidad)

    try:
        cursor.execute(query, params)
        resultados = cursor.fetchall()

        if resultados:
            sensores_disponibles = list(resultados[0].keys())
            sensores_disponibles.remove('timestamp')
            sensores_disponibles.remove('imagen')
        else:
            sensores_disponibles = sensores

        cursor.close()
        conn.close()

        export_query = str(request.query_params)

        return templates.TemplateResponse("consulta.html", {
            "request": request,
            "datos": ultimo,
            "resultados": resultados,
            "sensores": sensores_disponibles,
            "export_query": export_query,
            "desde": desde,
            "hasta": hasta,
            "cantidad": cantidad,
            "hora_inicio": hora_inicio,
            "hora_final": hora_final,
            "rango_ml8511": rango_ml8511,
            "rango_visible": rango_visible,
            "sin_limite": sin_limite
        })
    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en DB: {e}")
    
@router.get("/exportar")
async def exportar(
    request: Request,
    desde: str = None,
    hasta: str = None,
    cantidad: int = 10,
    hora_inicio: str = None,
    hora_final: str = None,
    sin_limite: int = 0
):
    columnas_validas = [
        "ml8511", "ml8511_2", "visible", "visible_2", "humedad", "temp_dht", "temp_bmp",
        "presion_bmp", "lat", "lng", "satelites", "altitud", "temp_max_c", "temp_max_f"
    ]

    sensores = request.query_params.getlist("sensores")
    sensores = [s for s in sensores if s in columnas_validas]
    if not sensores:
        sensores = ["ml8511"]

    try:
        conn = obtener_conexion()
        cursor = conn.cursor(dictionary=True)

        campos = ["timestamp"] + sensores + ["imagen"]
        query = f"SELECT {', '.join(campos)} FROM registros WHERE 1=1"
        params = []

        if desde:
            query += " AND timestamp >= ?"
            params.append(desde + " 00:00:00")
        if hasta:
            query += " AND timestamp <= ?"
            params.append(hasta + " 23:59:59")

        # Filtro por hora
        if hora_inicio and hora_final:
            query += " AND TIME(timestamp) BETWEEN ? AND ?"
            params.append(hora_inicio)
            params.append(hora_final)

        query += " ORDER BY timestamp DESC"
        if not sin_limite:
            query += " LIMIT ?"
            params.append(cantidad)

        cursor.execute(query, params)
        resultados = cursor.fetchall()

        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=campos)
        writer.writeheader()
        writer.writerows(resultados)
        csv_buffer.seek(0)

        zip_filename = "exported_data.zip"
        zip_path = os.path.join(IMAGE_DIR, zip_filename)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("data.csv", csv_buffer.getvalue())
            for row in resultados:
                imagen = row.get("imagen")
                if imagen:
                    imagen_path = os.path.join("imagenes", imagen.lstrip("/imagenes/"))
                    if os.path.exists(imagen_path):
                        zipf.write(imagen_path, os.path.basename(imagen_path))

        cursor.close()
        conn.close()

        return FileResponse(
            zip_path,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en DB: {e}")



@router.get("/exportar_sin_imagenes", response_class=FileResponse)
async def exportar_sin_imagenes(
    request: Request,
    desde: str = None,
    hasta: str = None,
    cantidad: int = 10
):
    columnas_validas = [ "ml8511", "visible"]

    # Obtener los parámetros de sensores desde la consulta
    sensores = request.query_params.getlist("sensores")
    sensores = [s for s in sensores if s in columnas_validas]
    if not sensores:
        sensores = ["ml8511"]

    conn = obtener_conexion()
    cursor = conn.cursor(dictionary=True)

    # Armar la query dinámica
    query = "SELECT timestamp, " + ", ".join(sensores) + " FROM registros WHERE 1=1"
    params = []

    if desde:
        query += " AND timestamp >= ?"
        params.append(desde + " 00:00:00")
    if hasta:
        query += " AND timestamp <= ?"
        params.append(hasta + " 23:59:59")

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(cantidad)

    try:
        cursor.execute(query, params)
        resultados = cursor.fetchall()

        # Crear el archivo CSV
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([ "ml8511", "visible", "timestamp"])

        for registro in resultados:
            # Escribir la fila en el CSV sin las imágenes
            csv_writer.writerow([ registro['ml8511'], registro['visible'], registro['timestamp']])

        csv_file.seek(0)

        # Guardar CSV temporalmente
        csv_filename = "datos_sensores_sin_imagenes.csv"
        csv_path = os.path.join(IMAGE_DIR, csv_filename)

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            f.write(csv_file.getvalue())

        # Devolver el archivo CSV como respuesta de descarga
        return FileResponse(csv_path, media_type='text/csv', filename=csv_filename)

    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en DB: {e}")
    

import zipfile
import os
import io
from fastapi.responses import StreamingResponse

@router.get("/descargar_imagenes")
async def descargar_imagenes(
    desde: str = None,
    hasta: str = None,
    cantidad: int = 10,
    hora_inicio: str = None,
    hora_final: str = None
):
    conn = obtener_conexion()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT imagen FROM registros WHERE 1=1"
    params = []

    if desde:
        query += " AND timestamp >= ?"
        params.append(desde + " 00:00:00")
    if hasta:
        query += " AND timestamp <= ?"
        params.append(hasta + " 23:59:59")
    if hora_inicio and hora_final:
        query += " AND TIME(timestamp) BETWEEN ? AND ?"
        params.append(hora_inicio)
        params.append(hora_final)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(cantidad)

    try:
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()

        print(f"Resultados obtenidos: {resultados}")
        if not resultados:
            raise HTTPException(status_code=404, detail="No se encontraron imágenes.")

        # Crear ZIP en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for fila in resultados:
                nombre_imagen = fila['imagen']
                # Quitar el prefijo
                nombre_imagen = nombre_imagen.removeprefix("/imagenes/")
                # Construir ruta completa
                ruta_imagen = os.path.join("imagenes", nombre_imagen)
                if os.path.exists(ruta_imagen):
                    zip_file.write(ruta_imagen, arcname=nombre_imagen)
                else:
                    print(f"Imagen no encontrada: {ruta_imagen}")

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=imagenes_exportadas.zip"}
        )

    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en DB: {e}")


# 📡 API para recibir datos desde ESP32
@router.post("/api/datos")
async def recibir_datos(data: SensorData, background_tasks: BackgroundTasks):
    print(f"Datos recibidos: {data}")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_imagen = f"{timestamp}.dng"
    ruta_imagen = os.path.join("imagenes", nombre_imagen)
    url_imagen = f"/imagenes/{nombre_imagen}"
    temp_raspberry = get_raspberry_temp()

    if temp_raspberry > 60:
        print(f"Temperatura de la Raspberry Pi alta: {temp_raspberry}°C - Activando ventilador")
        ventilador_state("on")
    else:
        ventilador_state("off")

    mover_a_posiciones(0)  # Destapar cubierta de la cámara
    background_tasks.add_task(capturar_y_guardar_imagen, nombre_imagen)
    mover_a_posiciones(1)  # Cerrar cubierta de la cámara

    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO registros (
                timestamp, ml8511, ml8511_2, visible, visible_2, humedad, temp_dht, temp_bmp, presion_bmp,
                lat, lng, satelites, altitud, fecha, hora, temp_max_c, temp_max_f, imagen, temp_raspberry
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp.replace('_', ' '),
            data.ml8511,
            data.ml8511_2,
            data.visible,
            data.visible_2,
            data.humedad,
            data.temp_dht,
            data.temp_bmp,
            data.presion_bmp,
            data.lat,
            data.lng,
            data.satelites,
            data.altitud,
            data.fecha,
            data.hora,
            data.temp_max_c,
            data.temp_max_f,
            url_imagen,
            temp_raspberry
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "ok"}
    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=f"Error en DB: {e}")

@router.get("/configuracion", response_class=HTMLResponse)
async def configuracion(request: Request):
    # Conexión a la base de datos
    conn = obtener_conexion()
    cur = conn.cursor()

    # Obtener 'frecuencia_peticion'
    cur.execute("SELECT valor FROM configuraciones WHERE nombre = 'frecuencia_peticion'")
    resultado = cur.fetchone()
    valor_actual = resultado[0] if resultado else 60

    # Obtener todos los parámetros configurables
    cur.execute("SELECT nombre, valor FROM configuraciones")
    configuraciones = cur.fetchall()

    # Crear un diccionario con los parámetros
    parametros = {nombre: valor for nombre, valor in configuraciones}
    print(f"Parámetros leídos de la base de datos: {parametros}")
    
    # Cerrar conexión
    cur.close()
    conn.close()

    print(parametros)
    # Pasar todos los parámetros al template
    return templates.TemplateResponse("configuracion.html", {
        "request": request,
        "valor_actual": parametros.get("frecuencia_peticion", 60),  # Si no existe, se asigna 60 por defecto
        "gain": parametros.get("AnalogueGain", 10),
        "exposure_time": parametros.get("ExposureTime", 10000),
        "ae_mode": parametros.get("AeEnable", 0),
        "awb_mode": parametros.get("AwbEnable", 1),
        "brightness": parametros.get("Brightness", 1),
        "contrast": parametros.get("Contrast", 1),
        "saturation": parametros.get("Saturation", 1),
        "sharpness": parametros.get("Sharpness", 1),
    })


@router.post("/configurar-sistema")
async def actualizar_frecuencia( request: Request,tiempoMuestreo: int = Form(...)):
    # Validar si el tiempo de muestreo es válido
    if tiempoMuestreo <= 0:
        raise HTTPException(status_code=400, detail="Tiempo de muestreo debe ser un valor positivo.")

    # Conexión a la base de datos
    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute("SELECT valor FROM configuraciones WHERE nombre = 'frecuencia_peticion'")
    resultado = cur.fetchone()

    valor_actual = tiempoMuestreo
    print(f"Tiempo de muestreo recibido: {tiempoMuestreo}")
    # Verificar si ya existe el parámetro 'frecuencia_peticion'
    cur.execute("SELECT id FROM configuraciones WHERE nombre = 'frecuencia_peticion'")
    resultado = cur.fetchone()

    if resultado:
        # Actualizar el valor existente
        cur.execute("UPDATE configuraciones SET valor = ? WHERE nombre = 'frecuencia_peticion'", (tiempoMuestreo,))
    else:
        # Insertar el nuevo valor si no existe
        cur.execute("INSERT INTO configuraciones (nombre, valor) VALUES ('frecuencia_peticion', ?)", (tiempoMuestreo,))

    conn.commit()
    cur.close()
    conn.close()
    return templates.TemplateResponse("configuracion.html", {"request": request, "valor_actual": valor_actual, "message": f"Frecuencia de petición actualizada a {tiempoMuestreo} segundos."})


@router.post("/configurar-camara")
async def configurar_camara(
    request: Request,
    gain: float = Form(...),
    exposure_time: int = Form(...),
    ae_mode: int = Form(...),
    awb_mode: int = Form(...),
    brightness: int = Form(...),
    contrast: int = Form(...),
    saturation: int = Form(...),
    sharpness: float = Form(...)
):
    # Validaciones básicas
    if gain < 0 or exposure_time <= 0 or sharpness < 0:
        raise HTTPException(status_code=400, detail="Parámetros inválidos.")

    parametros = {
        "AnalogueGain": gain,
        "ExposureTime": exposure_time,
        "AeEnable": ae_mode,
        "AwbEnable": awb_mode,
        "Brightness": brightness,
        "Contrast": contrast,
        "Saturation": saturation,
        "Sharpness": sharpness
    }

    conn = obtener_conexion()
    cur = conn.cursor()

    for nombre, valor in parametros.items():
        # Verificar si ya existe el parámetro
        cur.execute("SELECT id FROM configuraciones WHERE nombre = ?", (nombre,))
        existe = cur.fetchone()

        if existe:
            cur.execute("UPDATE configuraciones SET valor = ? WHERE nombre = ?", (valor, nombre))
        else:
            cur.execute("INSERT INTO configuraciones (nombre, valor) VALUES (?, ?)", (nombre, valor))

    conn.commit()
    cur.close()
    conn.close()

    return templates.TemplateResponse("configuracion.html", {
        "request": request,
        "valor_actual": parametros.get("frecuencia_peticion", 60),  # Si no existe, se asigna 60 por defecto
        "gain": parametros.get("AnalogueGain", 10),
        "exposure_time": parametros.get("ExposureTime", 10000),
        "ae_mode": parametros.get("AeEnable", 0),
        "awb_mode": parametros.get("AwbEnable", 1),
        "brightness": parametros.get("Brightness", 1),
        "contrast": parametros.get("Contrast", 1),
        "saturation": parametros.get("Saturation", 1),
        "sharpness": parametros.get("Sharpness", 1),
    })