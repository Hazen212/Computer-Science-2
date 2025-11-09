#include <Servo.h>

// --- I/O Pin Definitions ---

// Cảm biến Lối Vào (Entrance)
const int trigEntrance = 11;
const int echoEntrance = 12; 

// Cảm biến Lối Ra (Exit)
const int trigExit = 8;     
const int echoExit = 9;

// Cảm biến Cửa/Rào chắn Phụ (Door/Barrier)
const int trigDoor = 6;
const int echoDoor = 7;

// Cảm biến Đỗ Xe (IR/Analog)
const int irParkingPin1 = A0; 
const int irParkingPin2 = A1; 
const int irParkingPin3 = A2; 
const int irOccupiedThreshold = 500; // Ngưỡng phát hiện đỗ xe


// Servo
Servo gateServo;
const int servoPinGate = 10;
Servo doorServo;
const int servoPinDoor = 2; // Chân D2 cho Servo Cửa

// --- Biến Trạng Thái ---
bool parkingSpotOccupied1 = false;
bool parkingSpotOccupied2 = false;
bool parkingSpotOccupied3 = false;
int freeSpots = 3;

// --- Biến và Hằng số cho Servo ---
int currentDoorAngle = 0;      
const int closedDoorAngle = 0;
const int openDoorAngle = 90;
const int moveDelay = 15;      

// Ngưỡng phát hiện (cm)
const int detectDistance = 5; 
const int doorDistance = 10;  

// --- Hàm chức năng ---

// Hàm lấy khoảng cách từ cảm biến siêu âm
long getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return 999; 
  return duration * 0.034 / 2; 
}

// Hàm di chuyển Servo Cửa Phụ một cách từ từ
void moveDoorTo(int targetAngle) {
  if (targetAngle == currentDoorAngle) return; 

  if (targetAngle > currentDoorAngle) {
    for (int i = currentDoorAngle; i <= targetAngle; i++) {
      doorServo.write(i);
      delay(moveDelay);
    }
  } else {
    for (int i = currentDoorAngle; i >= targetAngle; i--) {
      doorServo.write(i);
      delay(moveDelay);
    }
  }
  currentDoorAngle = targetAngle;
}

void setup() {
  Serial.begin(9600);
  
  // 1. Khởi tạo chân Cảm biến Siêu âm
  pinMode(trigEntrance, OUTPUT); pinMode(echoEntrance, INPUT);
  pinMode(trigExit, OUTPUT); pinMode(echoExit, INPUT);
  pinMode(trigDoor, OUTPUT); pinMode(echoDoor, INPUT);

  // 2. Relay code đã bị loại bỏ

  // 3. Gắn Servo
  gateServo.attach(servoPinGate);
  doorServo.attach(servoPinDoor);
  
  gateServo.write(30); // Đóng Cổng Chính
  doorServo.write(closedDoorAngle); // Đóng Cửa Phụ
  currentDoorAngle = closedDoorAngle; 
  
  Serial.println("Core Smart Parking System Ready.");
}

void loop() {
  
  // --- A. Cập nhật trạng thái Bãi đỗ xe (IR Sensors) ---
  int irValue1 = analogRead(irParkingPin1);
  int irValue2 = analogRead(irParkingPin2);
  int irValue3 = analogRead(irParkingPin3);
  
  parkingSpotOccupied1 = (irValue1 < irOccupiedThreshold);
  parkingSpotOccupied2 = (irValue2 < irOccupiedThreshold);
  parkingSpotOccupied3 = (irValue3 < irOccupiedThreshold);
  
  freeSpots = (parkingSpotOccupied1 ? 0 : 1) + 
              (parkingSpotOccupied2 ? 0 : 1) + 
              (parkingSpotOccupied3 ? 0 : 1);
              
  // --- B. Logic điều khiển Relay qua Serial Monitor (ĐÃ BỊ LOẠI BỎ) ---
  // Mã code đọc Serial và điều khiển Relay đã bị xóa
  
  // --- C. Logic điều khiển Cổng Chính và Cửa Phụ (Ultrasonics & Servos) ---
  long distEntrance = getDistance(trigEntrance, echoEntrance);
  long distExit = getDistance(trigExit, echoExit);
  long distDoor = getDistance(trigDoor, echoDoor); 

  // 1. Logic Cổng Chính (Gate Servo)
  if ((distEntrance > 0 && distEntrance < detectDistance) || (distExit > 0 && distExit < detectDistance)) {
    Serial.print("Free Spots: "); Serial.println(freeSpots);
    // Code mở cổng nếu có xe
    Serial.println("Car detected at Entrance/Exit -> Gate OPEN (Quick)");
    gateServo.write(120);   
    delay(2000); 
  } 
  else {
    gateServo.write(30);    
  }
  
  // 2. Logic Cửa Phụ (Door Servo)
  if (distDoor > 0 && distDoor < doorDistance) {
    if (currentDoorAngle != openDoorAngle) {
        Serial.println("Object near Door -> Door OPENING Slowly");
        moveDoorTo(openDoorAngle); 
        delay(2000);
    }
  }
  else {
    if (currentDoorAngle != closedDoorAngle) {
        Serial.println("No object near Door -> Door CLOSING Slowly");
        moveDoorTo(closedDoorAngle); 
        delay(1000);
    }
  }
  
  // Debug trạng thái tổng hợp
  Serial.print("Entrance:"); Serial.print(distEntrance);
  Serial.print(" | Exit:"); Serial.print(distExit);
  Serial.print(" | Door:"); Serial.print(distDoor);
  Serial.print(" | Free:"); Serial.println(freeSpots);

  delay(200);
}
