import RPi.GPIO as GPIO
import time
import threading
from flask import Flask, render_template, jsonify

app = Flask(__name__)

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

# Variabel Global untuk Data Real-time
sensor_data = {
    "distance": 0,
    "motion": 0,
    "angle": 0,
    "status": "OFF"
}

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
    
    return round(((stop - start) * 34300) / 2, 1)

def sensor_loop():
    global sensor_data
    angles = [0, 45, 90, 135, 180, 135, 90, 45]
    while True:
        for a in angles:
            set_servo_angle(a)
            dist = get_distance()
            motion = GPIO.input(PIR)
            
            # Update State
            is_danger = (dist < 10 or motion == 1)
            sensor_data = {
                "distance": dist,
                "motion": motion,
                "angle": a,
                "status": "ON" if is_danger else "OFF"
            }

            # Update Hardware
            state = GPIO.HIGH if is_danger else GPIO.LOW
            GPIO.output(BUZZER, state)
            GPIO.output(LED, state)
            
            time.sleep(0.5)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    return jsonify(sensor_data)

if __name__ == '__main__':
    # Jalankan background thread untuk sensor
    t = threading.Thread(target=sensor_loop, daemon=True)
    t.start()
    
    # Mencari Alamat IP Lokal Otomatis
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip_local = s.getsockname()[0]
    except:
        ip_local = '127.0.0.1'
    finally:
        s.close()

    print(f"\n[SERVER AKTIF]")
    print(f"Akses Dashboard di Chrome: http://{ip_local}:5000\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
