from picamera2 import Picamera2, Preview
from cubierta import mover_a_posiciones
import time

picam2 = Picamera2()
camera_config = picam2.create_preview_configuration()
picam2.configure(camera_config)
mover_a_posiciones(0)
picam2.start()
time.sleep(2)
picam2.capture_file("test.jpg")
mover_a_posiciones(1)