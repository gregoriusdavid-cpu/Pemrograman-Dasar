import RPi.GPIO as GPIO
import time
import threading
import mysql.connector
from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# --- Konfigurasi Database ---
db_config = {
    'host': 'localhost',
    'user': 'root',      
    'password': '',      
    'database': 'log_history_scarecrow'
}

# --- Konfigurasi GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

TRIG, ECHO = 23, 24
BUZZER, LED = 18, 17
PIR, SERVO = 27, 12

GPIO.setup([TRIG, BUZZER, LED, SERVO], GPIO.OUT)
GPIO.setup([ECHO, PIR], GPIO.IN)

pwm_servo = GPIO.PWM(SERVO, 50)
pwm_servo.start(0)

# Variabel Global
current_data = {"distance": 0, "motion": 0, "angle": 0, "status": "OFF"}
last_db_update = 0  # Untuk melacak waktu upload ke MySQL

def set_servo_angle(angle):
    duty = angle / 18 + 2
    pwm_servo.ChangeDutyCycle(duty)
    time.sleep(0.2)
    pwm_servo.ChangeDutyCycle(0)

def get_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    start, stop = time.time(), time.time()
    while GPIO.input(ECHO) == 0: start = time.time()
    while GPIO.input(ECHO) == 1: stop = time.time()
    return int(((stop - start) * 34300) / 2)

def save_to_db(pear_val, ultrasonic_val):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = "INSERT INTO riwayat_scarecrow (pear, ultrasonic, tanggal) VALUES (%s, %s, %s)"
        cursor.execute(query, (pear_val, ultrasonic_val, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
        print("Data tersimpan ke MySQL (Interval 1 Menit)")
    except Exception as e:
        print(f"Database Error: {e}")

def sensor_loop():
    global current_data, last_db_update
    angles = [0, 45, 90, 135, 180, 135, 90, 45]
    
    while True:
        for a in angles:
            set_servo_angle(a)
            dist = get_distance()
            motion = GPIO.input(PIR)
            
            # Update data untuk Website (Setiap Detik/Scan)
            current_data = {
                "distance": dist, 
                "motion": motion, 
                "angle": a,
                "status": "ON" if (dist < 10 or motion == 1) else "OFF"
            }

            # Update Hardware
            state = GPIO.HIGH if current_data["status"] == "ON" else GPIO.LOW
            GPIO.output(BUZZER, state)
            GPIO.output(LED, state)

            # Logika Simpan ke DB (Setiap 60 detik)
            current_time = time.time()
            if current_time - last_db_update >= 60:
                # Jalankan simpan DB di thread berbeda agar tidak mengganggu scan
                threading.Thread(target=save_to_db, args=(motion, dist)).start()
                last_db_update = current_time
            
            time.sleep(0.5)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    db_logs = []
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM riwayat_scarecrow ORDER BY no DESC LIMIT 15")
        db_logs = cursor.fetchall()
        cursor.close()
        conn.close()
    except: pass

    return jsonify({"live": current_data, "logs": db_logs})

if __name__ == '__main__':
    threading.Thread(target=sensor_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)