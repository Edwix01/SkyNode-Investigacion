//Librerias
#include "driver/adc.h"      // diver del ADC
#include <Wire.h>           //I2C 
#include "BH1750.h"        //I2C
#include <PubSubClient.h> //MQTT
#include <HardwareSerial.h>
#include <TinyGPSPlus.h>
#include <Adafruit_BMP280.h>
#include "max6675.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_GFX.h>       //Para OLED
#include <Adafruit_SSD1306.h>   //Para OLED
#include "DHT.h"


//Credenciales WiFi
const char* ssid = "Edwin";
const char* password = "seed1234";

//const char* ssid = "Edwin-Lima";
//const char* password = "edwinlim123";

// Configuración MQTT

const int mqtt_port = 1883;
const char* mqtt_subscribe_topic = "raspberry/solicitar_datos";  // Tópico para recibir solicitudes
const char* mqtt_publish_topic = "esp32/respuesta";  // Tópico para publicar las respuestas
WiFiClient espClient;
PubSubClient client(espClient);

//Comunicación HTTP
const char* mqtt_broker = "192.168.137.5";  // IP de la Raspberry Pi o broker MQTT
const char* servidor = "http://192.168.137.5:8000/api/datos";  // Ruta API

//Configuración del ADC
adc1_channel_t channel_ADC1_2 = ADC1_CHANNEL_2;  //pin GPIO2
adc1_channel_t channel_ADC1_3 = ADC1_CHANNEL_3;  //pin GPIO3 
adc_atten_t atten = ADC_ATTEN_DB_11;   // también hay otras opciones; e.g., 2_5

//Variables de Control
unsigned long ultimoMensaje = 0;
const unsigned long tiempoEspera = 300000;  // 30 segundos (ajustable)


// Configuración del OLED
#define Screen_width 128
#define Screen_height 64
#define OLED_reset -1
#define Screen_address 0x3C
#define DHTPIN 0        //  GPIO 0
#define DHTTYPE DHT11   // Tipo de sensor (puede ser DHT11 o DHT22)
#define RXD2 5  // Conectado al TX del GPS
#define TXD2 4  // (Normalmente no necesario transmitir al GPS)
int thermoDO = 7;
int thermoCS = 9;
int thermoCLK = 6;

Adafruit_SSD1306 display(Screen_width, Screen_height, &Wire, OLED_reset);
BH1750 visible_light;   // sensor of natural light BH1750
BH1750 visible_light2;

//Nueva integración
// Sensor de Presion
Adafruit_BMP280 bmp; // use I2C interface
Adafruit_Sensor *bmp_temp = bmp.getTemperatureSensor();
Adafruit_Sensor *bmp_pressure = bmp.getPressureSensor();
//GPS
TinyGPSPlus gps;
HardwareSerial SerialGPS(1);
//Sensor de temperatura max
MAX6675 thermocouple(thermoCLK, thermoCS, thermoDO);
//DHT 11
DHT dht(DHTPIN, DHTTYPE);



//=================================================================
//                      SETUP
//=================================================================
void setup() {
  Serial.begin(115200);  // config com serial
  Wire.begin(18, 19);
   //configuracion OLED
  display.begin(SSD1306_SWITCHCAPVCC, Screen_address);
  display.clearDisplay();
  display.display();
  delay(1000);

  //Iniciailización WiFi-MQTT
  conectarWiFi();

  //Inicialización ADC
  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten(channel_ADC1_2, atten);
  adc1_config_channel_atten(channel_ADC1_3, atten);
  // config of visible light sensor
  visible_light.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x23, &Wire);
  visible_light2.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x5C, &Wire);
  //Nuevo Presion
  unsigned status;
  //status = bmp.begin(BMP280_ADDRESS_ALT, BMP280_CHIPID);
  status = bmp.begin(0x76);
  if (!status) {
    String mensaje = "Error: BMP280 no detectado";
    Serial.println(mensaje);

    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println(mensaje);
    
    uint8_t sensorID = bmp.sensorID();
    String idMensaje = "ID: 0x" + String(sensorID, HEX);
    Serial.println(idMensaje);
    display.setCursor(0, 10);
    display.println(idMensaje);
    display.display();

    while (1) delay(10);  // detener ejecución
  }
  /* Default settings from datasheet. */
  bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,     /* Operating Mode. */
                  Adafruit_BMP280::SAMPLING_X2,     /* Temp. oversampling */
                  Adafruit_BMP280::SAMPLING_X16,    /* Pressure oversampling */
                  Adafruit_BMP280::FILTER_X16,      /* Filtering. */
                  Adafruit_BMP280::STANDBY_MS_500); /* Standby time. */

  bmp_temp->printSensorDetails();
  // Inicializar UART1 para GPS
  Serial.println("Iniciando comunicación con GPS...");  
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Iniciando GPS...");
  display.display();
  delay(500);
  SerialGPS.begin(9600, SERIAL_8N1, RXD2, TXD2);
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("GPS Iniciado...");
  display.display();
  delay(1000);

  //DHT11
  Serial.println("Iniciando sensor DHT11...");
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Iniciando DHT11...");
  display.display();
  delay(500);
  dht.begin();
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("DHT11 Iniciado...");
  display.display();
  delay(1000);

  client.setServer(mqtt_broker, mqtt_port);
  client.setCallback(callback);
  ultimoMensaje = millis();
}


//=================================================================
//                      Funciones de MQTT
//=================================================================
// Función que se ejecuta cuando se recibe un mensaje en el tópico suscrito
void callback(char* topic, byte* payload, unsigned int length) {
  String mensaje = "";
  for (int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }
  
  // Si se recibe la solicitud de datos
  if (String(topic) == mqtt_subscribe_topic && mensaje == "solicitar_datos") {
    // Aquí se pueden incluir los valores de los sensores que deseas enviar
    send_rasp();
    Serial.println("Datos enviados correctamente");
  }
}
// Conectar al broker MQTT
void reconnect() {
  while (!client.connected()) {
    String mensaje = "Intentando conectar al broker MQTT...";
    Serial.println(mensaje);
    
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println(mensaje);
    display.display();

    if (client.connect("ESP32Client")) {
      mensaje = "Conectado al broker MQTT";
      Serial.println(mensaje);
      
      display.setCursor(0, 20);
      display.println(mensaje);
      display.display();
      client.subscribe(mqtt_subscribe_topic);  // Suscribirse al tópico
      mostrarMensajeEspera();

    } else {
      mensaje = "Error al conectar, rc=" + String(client.state());
      Serial.println(mensaje);
      
      display.setCursor(0, 20);
      display.println(mensaje);
      display.display();
      
      delay(2000);
    }
  }
}

//=================================================================
//           Funciones de Envío de Datos a Raspberry
//=================================================================
void send_rasp() {
  ultimoMensaje = millis();  // Actualiza cada vez que recibe solicitud
  Serial.println("---------------------INICIO------------------");
  while (SerialGPS.available() > 0) {
    gps.encode(SerialGPS.read());
  }
  int uv_ml8511_1 = adc1_get_raw(channel_ADC1_3);
  int uv_ml8511_2 = adc1_get_raw(channel_ADC1_2);
  int vis_light_level = visible_light.readLightLevel();
  int vis_light_level_2 = visible_light2.readLightLevel();
  float humedad = dht.readHumidity();
  float temperatura = dht.readTemperature();
  sensors_event_t temp_event, pressure_event;
  bmp_temp->getEvent(&temp_event);
  bmp_pressure->getEvent(&pressure_event);
  float temp_bmp = temp_event.temperature;
  float presion_bmp = pressure_event.pressure;
  float lat = 0.0;
  float lng = 0.0;
  int satelites = 0;
  float altitud = 0.0;
  String fecha = "";
  String hora = "";

  if (isnan(humedad) || isnan(temperatura)) {
    Serial.println("¡Fallo al leer del sensor DHT11!");
    return;
  }

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);

  display.println("ML8511: " + String(uv_ml8511_1));
  display.println("ML8511_2: " + String(uv_ml8511_2));
  display.println("BH1750: " + String(vis_light_level));
  display.println("BH1750_2: " + String(vis_light_level_2));
  display.println("BMP 280*C: " + String(temp_bmp));
  display.println("BMP 280hPa: " + String(presion_bmp));



  Serial.print("Humedad: "); Serial.print(humedad); Serial.print(" %\t");
  Serial.print("Temperatura: "); Serial.println(temperatura);
  Serial.println("ML8511: " + String(uv_ml8511_1));
  Serial.println("ML8511_2: " + String(uv_ml8511_2));
  Serial.println("BH1750: " + String(vis_light_level));
  Serial.println("BH1750-2: " + String(vis_light_level_2));
  Serial.println("BMP 280*C: " + String(temp_bmp));
  Serial.println("BMP 280hPa: " + String(presion_bmp));

  lat = gps.location.lat();
  lng = gps.location.lng();
  satelites = gps.satellites.value();
  altitud = gps.altitude.meters();
  fecha = String(gps.date.day()) + "/" + String(gps.date.month()) + "/" + String(gps.date.year());
  hora = String(gps.time.hour()) + ":" + String(gps.time.minute()) + ":" + String(gps.time.second());

  display.println("Lat: " + String(lat, 6));
  display.println("Lng: " + String(lng, 6));

  Serial.println("Latitud: " + String(lat, 6));
  Serial.println("Longitud: " + String(lng, 6));
  Serial.println("Satélites: " + String(satelites));
  Serial.println("Altitud: " + String(altitud) + " m");
  Serial.println("Fecha: " + fecha);
  Serial.println("Hora: " + hora);

  float temp_max_c = thermocouple.readCelsius();
  float temp_max_f = thermocouple.readFahrenheit();
  Serial.println("MAX Temperatura C: " + String(temp_max_c));
  Serial.println("MAX Temperatura F: " + String(temp_max_f));
  Serial.println("---------------------FIN------------------");

  display.display();

  enviarDatos( uv_ml8511_1,uv_ml8511_2, vis_light_level,vis_light_level_2, humedad, temperatura, temp_bmp, presion_bmp,
              lat, lng, satelites, altitud, fecha, hora, temp_max_c, temp_max_f);

  delay(100);
}

void enviarDatos(int ml8511, int ml8511_2, int visible,int visible_2, float humedad, float temp_dht, float temp_bmp, float presion_bmp,
                 float lat, float lng, int sats, float alt, String fecha, String hora,
                 float temp_max_c, float temp_max_f) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(servidor);
    http.addHeader("Content-Type", "application/json");

    String json = "{";
    json += "\"ml8511\":" + String(ml8511) + ",";
    json += "\"ml8511_2\":" + String(ml8511_2) + ",";
    json += "\"visible\":" + String(visible) + ",";
    json += "\"visible_2\":" + String(visible_2) + ",";
    json += "\"humedad\":" + String(humedad) + ",";
    json += "\"temp_dht\":" + String(temp_dht) + ",";
    json += "\"temp_bmp\":" + String(temp_bmp) + ",";
    json += "\"presion_bmp\":" + String(presion_bmp) + ",";
    json += "\"lat\":" + String(lat, 6) + ",";
    json += "\"lng\":" + String(lng, 6) + ",";
    json += "\"satelites\":" + String(sats) + ",";
    json += "\"altitud\":" + String(alt) + ",";
    json += "\"fecha\":\"" + fecha + "\",";
    json += "\"hora\":\"" + hora + "\",";
    json += "\"temp_max_c\":" + String(temp_max_c) + ",";
    json += "\"temp_max_f\":" + String(temp_max_f);
    json += "}";

    int httpResponseCode = http.POST(json);
    Serial.print("Código HTTP: ");
    Serial.println(httpResponseCode);

    if (httpResponseCode > 0) {
      String respuesta = http.getString();
      Serial.println("Respuesta del servidor:");
      Serial.println(respuesta);
    } else {
      Serial.println("Error al enviar datos");
       // Mostrar en pantalla solo si falla
      display.clearDisplay();
      display.setTextSize(1);
      display.setTextColor(SSD1306_WHITE);
      display.setCursor(0, 0);
      display.println("Error HTTP");
      display.setCursor(0, 10);
      display.print("Codigo: ");
      display.println(httpResponseCode);
      display.display();
    }
    http.end();
  } else {
     display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("WiFi no conectado");
    display.display();
  }
}

//=================================================================
//                      Funciones de WiFi
//=================================================================
void conectarWiFi() {
  WiFi.begin(ssid, password);
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Conectando a WiFi");
  display.display();
  
  int puntos = 0;
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    puntos = (puntos + 1) % 4;  // 0, 1, 2, 3

    display.setCursor(0, 10);
    display.print("Cargando");
    for (int i = 0; i < puntos; i++) {
      display.print(".");
    }
    display.print("    "); // Borra sobrantes si hay menos puntos
    display.display();
  }
  Serial.println("\nConectado a WiFi");
  Serial.println(WiFi.localIP());
  display.setCursor(0, 30);
  display.println("WiFi conectado!");
  display.setCursor(0, 40);
  display.print("IP: ");
  display.println(WiFi.localIP());
  display.display();
  delay(2000);  // Pausa breve para ver el mensaje de éxito
}




void mostrarMensajeEspera() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Sistema iniciado");
  display.println("Esperando peticiones");
  display.display();
}

//=================================================================
//                      Loop
//=================================================================
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();  // Mantener la conexión y escuchar mensajes
  if (millis() - ultimoMensaje > tiempoEspera) {
    mostrarMensajeEspera();
    // Para que no siga reescribiendo todo el tiempo el mensaje
    ultimoMensaje = millis();  
  }

  delay(10);
}
