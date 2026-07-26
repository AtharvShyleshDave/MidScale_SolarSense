#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

#define LDR_PIN 34
#define ACS_PIN 35
#define DHTPIN 4
#define DHTTYPE DHT22

const char* ssid = "Redmi Note 13 5G";
const char* password = "AtharvDave";

const char* server = "http://10.31.214.244:5000/predict";

float temperature;
float irradiance;
float current;

float offsetVoltage = 1.65;
float sensitivity = 0.185;

DHT dht(DHTPIN, DHTTYPE);

void setup() {

  Serial.begin(115200);
  dht.begin();

  randomSeed(analogRead(32));

  WiFi.begin(ssid, password);

  Serial.println("Connecting to WiFi...");

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting...");
  }

  Serial.println("WiFi Connected");
}

void loop() {

  // ---------- CURRENT SENSOR ----------
  int adcCurrent = analogRead(ACS_PIN);

  float voltage = adcCurrent * (3.3 / 4095.0) + 1;

  current = ((voltage - offsetVoltage) / sensitivity);

  if (abs(current) < 0.05) current = 0;

  // ---------- PRACTICAL POWER ----------
  float practicalPower = voltage * current;
  float scaledPracticalPower = practicalPower;

  // ---------- TEMPERATURE (DHT22) ----------
  temperature = dht.readTemperature();

  if (isnan(temperature)) {
    Serial.println("DHT read failed");
    temperature = 0;
  }

  // ---------- LDR ----------
  irradiance = analogRead(LDR_PIN);

  Serial.println("Sensor Values:");

  Serial.print("Temperature: ");
  Serial.println(temperature);

  Serial.print("Irradiance: ");
  Serial.println(irradiance);

  Serial.print("Current: ");
  Serial.println(current);

  Serial.println("PRACTICAL POWER:");
  Serial.println(scaledPracticalPower * 8);

  HTTPClient http;

  http.begin(server);
  http.addHeader("Content-Type", "application/json");

  String json = "{\"TEMP\":" + String(temperature) +
                ",\"IRR\":" + String(irradiance) +
                ",\"DC_Current\":" + String(current) + "}";

  int httpResponseCode = http.POST(json);

  if (httpResponseCode > 0) {

    String response = http.getString();

    Serial.println("Prediction from Flask:");
    Serial.println(response);

    // --------- EXTRACT POWER_MID ----------
    int startIndex = response.indexOf("POWER_MID");
    int colonIndex = response.indexOf(":", startIndex);
    int endIndex = response.indexOf("}", colonIndex);

    String powerMidStr = response.substring(colonIndex + 1, endIndex);
    float powerMid = powerMidStr.toFloat();

    float scaledPowerMid = powerMid;

    Serial.println("POWER_MID:");
    Serial.println(scaledPowerMid);
  }

  else {
    Serial.print("Error sending POST: ");
    Serial.println(httpResponseCode);
  }

  http.end();

  delay(5000);
}