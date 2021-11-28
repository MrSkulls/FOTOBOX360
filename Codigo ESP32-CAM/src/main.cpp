#include <WiFi.h>
#include <HTTPClient.h> 
#include "esp_camera.h"
#include "soc/soc.h"           // Disable brownour problems
#include "soc/rtc_cntl_reg.h"  // Disable brownour problems
#include "driver/rtc_io.h"
#include <SPIFFS.h>
#include <FS.h>
#include <rBASE64.h>
#include <Stepper.h>

// Pin 12 ligado ao IN1 do ULN2003 driver
// Pin 13 ligado ao IN2 do ULN2003 driver
// Pin 14 ligado ao IN3 do ULN2003 driver
// Pin 15 ligado ao IN4 do ULN2003 driver
const int stepsPerRevolution = 2048;
Stepper myStepper = Stepper(stepsPerRevolution, 12, 14, 13, 15);

//Necessario atualizar com SSID e PASSWORD desejados
const char* ssid = "iPhone de Hugo Gomes";
const char* password =  "olahuguinho";


//Variaveis Globais
String payload;
File file;
HTTPClient http;

//Introduzir o URL do website
String Server = "http://192.168.1.127:8080";

// Photo File Name to save in SPIFFS
#define FILE_PHOTO "/photo.jpg"
#define nSerie 1000
// OV2640 camera module pins (CAMERA_MODEL_AI_THINKER)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22


camera_fb_t * fb = NULL; 
  
//Tira fotografia e transfere para BASE64
String tirarFoto( ){

    fb = esp_camera_fb_get();  

    if(!fb) {
      Serial.println("Camera capture failed");
      return "";
    }
  
    String imageFile = "data:image/jpeg;base64,";
    
    char *input = (char *)fb->buf;
    char output[rbase64_enc_len(3)];
    for (int i=0;i<fb->len;i++) {
      rbase64_encode(output, (input++), 3);
      if (i%3==0){
        imageFile.concat(String(output));
      } 
      
    }

    esp_camera_fb_return(fb);
    
    return imageFile;
}

void setup() {
 
  //Port Serial para debbug
  Serial.begin(115200);

  //Conexão com Wifi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }

  //Desligar 'brownout detector'
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  //modulo camera OV2640  
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
 

   if (psramFound()) {
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  //Inicio da camara
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    ESP.restart();
  }

  //Diminui o tamanho do quadro para uma taxa de quadros inicial mais alta
  sensor_t * s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_XGA);
  s->set_quality(s,11);


 
}

void loop() {
 
  if ((WiFi.status() == WL_CONNECTED)) { 
  
    //Recebe o numero de Fotografias que o ESP32 tem que tirar
    http.begin(Server + "/tirarfotos/" + nSerie);
    http.GET();                                        
    payload = http.getString();
    http.end();

    Serial.println(payload);

    //Converte String para Inteiro 
    int Numero = payload.toInt();

    if (Numero > 0){
      //Divisao 360º pelo numero de fotografias pedidas
      int Steps = stepsPerRevolution/Numero;

      //Definição da velocidade do motor
      myStepper.setSpeed(10);
     

    //Enquanto o numero de Fotos tiradas for maior que 0 
      while(Numero != 0){
        myStepper.step(Steps);
        delay(500);
        //Envio da fotografia em Base64 para o Website
        http.begin(Server + "/armazenar/"+ nSerie);
        http.POST(tirarFoto()); 
        http.end();
      

        Numero--;

        if(Numero == 0){
          //Ativa script para atualizar o valor das fotografias para 0
          http.begin(Server + "/atualizar/" + nSerie);
          http.GET(); 
          http.end();
        }
  
      }

    }

        
  }
  delay(2000);
 
}