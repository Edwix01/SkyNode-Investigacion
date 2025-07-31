# Sistema de Adquisición de Datos con ESP32-C3

Este proyecto implementa un sistema de adquisición de datos meteorológicos y ambientales utilizando un microcontrolador **ESP32-C3-MINI-1**. Los datos recopilados se transmiten de forma inalámbrica mediante el protocolo **MQTT**, aunque también se ha dejado habilitada la opción de transmisión vía UART hacia una Raspberry Pi.

## 🧩 Componentes y Conexiones

El sistema incorpora los siguientes sensores y módulos:

| Sensor / Módulo                    | Descripción                                  | Etiqueta     | Pin GPIO       | Protocolo    |
|----------------------------------|----------------------------------------------|--------------|----------------|--------------|
| Sensor UV 1                      | Radiación ultravioleta                       | `S_UV1`      | GPIO2          | Analógico    |
| Sensor UV 2                      | Radiación ultravioleta                       | `S_UV2`      | GPIO3          | Analógico    |
| Sensor de temperatura y humedad | Sensor digital DHT11                         | `DHT11`      | GPIO0          | Digital      |
| GPS                              | Módulo de posicionamiento satelital          | `RX_GPS`, `TX_GPS` | GPIO5 (RX), GPIO4 (TX) | UART         |
| Sensor de luz visible           | Sensor BH1750                                |              | I2C (`SDA`, `SCL`) | I2C      |
| Sensor barométrico              | Sensor BMP280 (temperatura y presión)        |              | I2C (`SDA`, `SCL`) | I2C      |
| Pantalla OLED                   | Display para visualizar datos en tiempo real |              | I2C (`SDA`, `SCL`) | I2C      |
| Termopar (SPI)                  | Sensor de temperatura de alta precisión      | `CS`, `SO`, `SCK` | GPIO9, GPIO7, GPIO6 | SPI        |

## 🔧 Comunicación

- **MQTT**: Transmisión inalámbrica principal hacia el servidor.
- **UART**: Pines reservados (`TX_UART` y `RX_UART`) para posible comunicación con una Raspberry Pi.
- **SPI**: Conexión al termopar.
- **I2C**: Conexión compartida por el sensor barométrico, sensor de luz y la pantalla OLED.

## 📷 Diagrama de Conexiones

A continuación, se muestra el esquema de conexiones del sistema:

<img width="1266" height="713" alt="Diagrama de Conexiones (1)" src="https://github.com/user-attachments/assets/e87ad0dd-0223-425e-8dd2-ed0c1b47cf80" />

---

## 💡 Notas

- Asegúrate de alimentar correctamente los dispositivos con 3.3V o 5V según sus requerimientos.
- Las señales analógicas de los sensores UV deben conectarse a pines que admitan entrada analógica en el ESP32-C3.
- El sistema puede ampliarse para incluir nuevos sensores que se comuniquen por I2C, UART o SPI.

---

## 📁 Estructura del Proyecto

