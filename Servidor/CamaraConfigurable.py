import os
import time
from picamera2 import Picamera2
from picamera2.controls import Controls

class CamaraPi:
    def __init__(self, 
                 output_folder="imagenes", 
                 gain=1.0, 
                 exposure_time=10,  # Tiempo de exposición en microsegundos
                 brightness=0.5, 
                 contrast=1.0, 
                 saturation=1.0, 
                 ae_mode=True,
                 aw_mode=True,
                 sharpness=1.0):
        """
        Clase para capturar imágenes RAW con parámetros configurables.
        
        Parámetros:
        - output_folder: Carpeta donde se guardarán las imágenes.
        - gain: Ganancia analógica (0.0–8.0).
        - brightness: Brillo (0.0–1.0).
        - contrast: Contraste (0.0–32.0).
        - saturation: Saturación (0.0–4.0).
        - sharpness: Nitidez (0.0–16.0).
        """
        # Preparar carpeta de salida
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(script_dir, output_folder)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Parámetros de captura
        self.params = {
            "AnalogueGain": gain,        # Sensibilidad ISO (máximo razonable sin mucho ruido)
            "ExposureTime": exposure_time,      # Tiempo de exposición en microsegundos (40 ms)
            "Brightness": brightness,          # Brillo digital
            "Contrast": contrast,            # Contraste más alto
            "Saturation": saturation,          # Ligeramente reducida para evitar ruido cromático
            "Sharpness":sharpness,           # Nitidez básica
            "AeEnable": ae_mode,          # Desactivar autoexposición (porque seteamos manualmente)
            "AwbEnable": aw_mode           # Mantener auto balance de blancos
        }
        
        print(f"Configurando cámara con: {self.params}")    
        # Inicializar cámara
        self.picam2 = Picamera2()
        # Configurar para STILL + RAW
        self.capture_config = self.picam2.create_still_configuration(raw={})


        
    def close(self):
        try:
            self.picam2.stop()
            self.picam2.close()
        except Exception as e:
            print(f"Error al cerrar la cámara: {e}")

    def autofocus(self):
        """
        Activar el enfoque automático (si la cámara lo soporta).
        """
        try:
            with self.picam2.controls as ctrl:
                # Si la cámara tiene un control de enfoque
                ctrl.FocusMode = 'Auto'  # Activar enfoque automático
                print("Enfoque automático activado.")
        except Exception as e:
            print(f"Error al activar el enfoque automático: {e}")

    def capture_raw(self, filename="imagen_raw.dng"):
        """
        Captura una imagen RAW y la guarda en el archivo especificado.
        
        Parámetros:
        - filename: Nombre del archivo DNG de salida.
        """
        config = self.picam2.create_still_configuration(
            raw={},  # Activar RAW
        )
        #Importante descomentar ....

        self.picam2.configure(config)
        # Aplicar controles antes de la captura
        self.picam2.set_controls(self.params)  # Aplica los parámetros a la cámara
        
        # hasta aqui ==========
        # Arrancar cámara
        self.picam2.start()
        time.sleep(2)  # Esperar a estabilizar el sensor
        # Construir ruta de salida
        output_path = os.path.join(self.output_dir, filename)
        # Cambiar a modo STILL/RAW y capturar
        self.picam2.switch_mode_and_capture_file(
            self.capture_config,
            output_path,
            name="raw"
        )
        print(f"📸 Imagen RAW capturada en: {output_path}")
        # Detener la cámara
        self.picam2.stop()


    def capture_raw_and_jpeg(self, raw_filename="imagen_raw.dng", jpeg_filename="imagen.jpg"):
        """
        Captura una imagen RAW y una JPEG, y las guarda en archivos separados.
        
        Parámetros:
        - raw_filename: Nombre del archivo RAW (.dng).
        - jpeg_filename: Nombre del archivo JPEG (.jpg).
        """
        # Configurar para captura con RAW + JPEG
        config = self.picam2.create_still_configuration(
            raw={},  # Activar RAW
        )
              # Aplicar controles antes de la captura
        self.picam2.set_controls(self.params)  # Aplica los parámetros a la cámara

        self.picam2.configure(config)

  
        # Arrancar cámara
        self.picam2.start()
        time.sleep(2)  # Esperar estabilización


        # Construir rutas
        raw_path = os.path.join(self.output_dir, raw_filename)
        jpeg_path = os.path.join(self.output_dir, jpeg_filename)

        # Capturar imagen y guardar
        request = self.picam2.capture_request()

        # Guardar imagen RAW
        try:
            request.save("raw", raw_path)
            print(f"📸 Imagen RAW capturada en: {raw_path}")
        except Exception as e:
            print(f"Error al guardar imagen RAW: {e}")

        # Guardar imagen JPEG
        try:
            request.save("main", jpeg_path)
            print(f"🖼️ Imagen JPEG capturada en: {jpeg_path}")
        except Exception as e:
            print(f"Error al guardar imagen JPEG: {e}")

        request.release()
        self.picam2.stop()
