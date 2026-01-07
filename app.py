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

sensor_data = {"distance": 0, "motion": 0, "angle": 0, "status": "OFF"}

def set_servo_angle(angle):
    duty = angle / 18 + 2
    pwm_servo.ChangeDutyCycle(duty)
    time.sleep(0.15)
    pwm_servo.ChangeDutyCycle(0)

def get_distance():
    # Pastikan TRIG Low
    GPIO.output(TRIG, False)
    time.sleep(0.01)
    
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    
    start_time = time.time()
    stop_time = time.time()
    
    # Timeout 0.1 detik untuk mencegah infinite loop/stuck
    timeout = time.time() + 0.1

    while GPIO.input(ECHO) == 0:
        start_time = time.time()
        if start_time > timeout: return 999 # Jika stuck, anggap jarak jauh

    while GPIO.input(ECHO) == 1:
        stop_time = time.time()
        if stop_time > timeout: return 999

    duration = stop_time - start_time
    distance = (duration * 34300) / 2
    return round(distance, 1)

def sensor_loop():
    global sensor_data
    angles = [0, 45, 90, 135, 180, 135, 90, 45]
    while True:
        for a in angles:
            set_servo_angle(a)
            dist = get_distance()
            motion = GPIO.input(PIR)
            
            # Kriteria Bahaya
            is_danger = (dist < 20 or motion == 1) # Ubah jarak sesuai kebutuhan
            sensor_data = {
                "distance": dist if dist < 400 else "Out of Range",
                "motion": motion,
                "angle": a,
                "status": "ON" if is_danger else "OFF"
            }

            GPIO.output(BUZZER, GPIO.HIGH if is_danger else GPIO.LOW)
            GPIO.output(LED, GPIO.HIGH if is_danger else GPIO.LOW)
            time.sleep(0.4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    return jsonify(sensor_data)

if __name__ == '__main__':
    t = threading.Thread(target=sensor_loop, daemon=True)
    t.start()
    
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip_local = s.getsockname()[0]
    except: ip_local = '127.0.0.1'
    finally: s.close()

    print(f"\nSERVER RUNNING: http://{ip_local}:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
