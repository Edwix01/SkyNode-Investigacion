# database.py
import mariadb
from collections import defaultdict
from datetime import datetime
from typing import List
from pydantic import BaseModel

# Conexión a la base de datos
def obtener_conexion():
    return mariadb.connect(
        user="usuario",
        password="contrasena",
        host="127.0.0.1",
        port=3306,
        database="sensores"
    )

# Clase para manejar los datos gráficos de los sensores
class SensorDataGraficos(BaseModel):
    g_labels: List[str]
    g_ml8511: List[float]
    g_ml8511_2: List[float]
    g_visible: List[float]
    g_visible_2: List[float]
    g_humedad: List[float]
    g_temp_dht: List[float]
    g_temp_bmp: List[float]
    g_presion_bmp: List[float]
    g_altitud: List[float]
    g_temp_max_c: List[float]
    g_temp_max_f: List[float]
    g_temp_raspberry: List[float]  

# Obtener datos de la base de datos según el rango de tiempo
def get_data_from_db(time_range: str, start: str = None, end: str = None):
    conn = obtener_conexion()
    cursor = conn.cursor()

    campos = [
        "ml8511", "ml8511_2", "visible", "visible_2", "humedad", "temp_dht",
        "temp_bmp", "presion_bmp", "altitud", "temp_max_c", "temp_max_f", "temp_raspberry"
    ]
     # Si hay filtro por fecha, mostrar cada muestra individual
    if start or end:
        label_sql = "timestamp"
        base_where = "1=1"
        where_clauses = [base_where]
        params = []
        if start:
            where_clauses.append("timestamp >= %s")
            params.append(start.replace("T", " "))
        if end:
            where_clauses.append("timestamp <= %s")
            params.append(end.replace("T", " "))
        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT {label_sql}, {', '.join(campos)}
            FROM registros
            WHERE {where_sql}
            ORDER BY timestamp
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()

        labels = []
        datos = {campo: [] for campo in campos}
        for row in rows:
            # row[0] es timestamp
            ts = row[0]
            # Si solo un día, mostrar solo hora; si varios días, mostrar fecha y hora
            if start and end and start[:10] == end[:10]:
                label = ts.strftime("%H:%M")
            else:
                label = ts.strftime("%d-%m-%Y %H:%M")
            labels.append(label)
            for idx, campo in enumerate(campos, start=1):
                datos[campo].append(row[idx] if row[idx] is not None else 0)

        conn.close()
        return SensorDataGraficos(
            g_labels=labels,
            g_ml8511=datos["ml8511"],
            g_ml8511_2=datos["ml8511_2"],
            g_visible=datos["visible"],
            g_visible_2=datos["visible_2"],
            g_humedad=datos["humedad"],
            g_temp_dht=datos["temp_dht"],
            g_temp_bmp=datos["temp_bmp"],
            g_presion_bmp=datos["presion_bmp"],
            g_altitud=datos["altitud"],
            g_temp_max_c=datos["temp_max_c"],
            g_temp_max_f=datos["temp_max_f"],
            g_temp_raspberry=datos["temp_raspberry"],
        )

    # Construir la base de la consulta según el rango
    if time_range == 'dia':
        label_sql = "HOUR(timestamp) AS label"
        base_where = "timestamp >= CURDATE() - INTERVAL 1 DAY"
    elif time_range == 'semana':
        label_sql = "DAYOFWEEK(timestamp) AS label"
        base_where = "timestamp >= CURDATE() - INTERVAL 7 DAY"
    elif time_range == 'mes':
        label_sql = "DAY(timestamp) AS label"
        base_where = "timestamp >= CURDATE() - INTERVAL 30 DAY"
    else:
        label_sql = "timestamp AS label"
        base_where = "1=1"

    # Agregar filtro por fechas si se proporcionan
    where_clauses = [base_where]
    params = []

    if start:
        where_clauses.append("timestamp >= %s")
        params.append(start.replace("T", " "))
    if end:
        where_clauses.append("timestamp <= %s")
        params.append(end.replace("T", " "))

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT {label_sql}, {', '.join(campos)}
        FROM registros
        WHERE {where_sql}
        ORDER BY timestamp
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()


    # Agrupar los datos para agregación
    data = defaultdict(lambda: {campo: [] for campo in campos})

    for row in rows:
        label = str(row[0])
        for idx, campo in enumerate(campos, start=1):
            data[label][campo].append(row[idx])

    # Promediar los valores para cada grupo
    labels = []
    promedios = {campo: [] for campo in campos}

    for label, valores in data.items():
        labels.append(label)
        for campo in campos:
            # Filtrar valores None
            valores_validos = [v for v in valores[campo] if v is not None]
            if valores_validos:
                promedios[campo].append(sum(valores_validos) / len(valores_validos))
            else:
                promedios[campo].append(0)

    conn.close()
    return SensorDataGraficos(
        g_labels=labels,
        g_ml8511=promedios["ml8511"],
        g_ml8511_2=promedios["ml8511_2"],
        g_visible=promedios["visible"],
        g_visible_2=promedios["visible_2"],
        g_humedad=promedios["humedad"],
        g_temp_dht=promedios["temp_dht"],
        g_temp_bmp=promedios["temp_bmp"],
        g_presion_bmp=promedios["presion_bmp"],
        g_altitud=promedios["altitud"],
        g_temp_max_c=promedios["temp_max_c"],
        g_temp_max_f=promedios["temp_max_f"],
        g_temp_raspberry=promedios["temp_raspberry"],
    )

def obtener_valor_configuracion(nombre_parametro: str) -> str:
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuraciones WHERE nombre = %s", (nombre_parametro,))
        resultado = cursor.fetchone()

        if resultado:
            return resultado[0]  # resultado es una tupla como ('60',)
        else:
            raise ValueError(f"Parámetro '{nombre_parametro}' no encontrado en la tabla configuraciones.")

    except mariadb.Error as e:
        print(f"Error al conectar con la base de datos: {e}")
        raise
    finally:
        if conn:
            conn.close()