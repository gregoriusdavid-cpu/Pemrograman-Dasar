# sensor_detector.py
# A Python script to monitor multiple sensors (PIR, IR, Ultrasonic) and control a Buzzer.
# Remember: Run script with elevated privileges (sudo python3 sensor_detector.py)
# Ensure RPi.GPIO library is installed.

import RPi.GPIO as GPIO
import time



PIR_SENSOR_PIN = 17 # PIR Sensor (Digital Input)
IR_SENSOR_PIN = 27  # IR Obstacle Sensor (Digital Input)

BUZZER_PIN = 22     # Buzzer (Output)
TRIG_PIN = 23       # Ultrasonic Trigger (Output)
ECHO_PIN = 24       # Ultrasonic Echo (Input)

SPEED_OF_SOUND = 34300  # Speed of sound in cm/s
DISTANCE_THRESHOLD = 15 # Distance in cm to trigger the buzzer

def setup():
    """Initializes GPIO settings for all components."""
    GPIO.setmode(GPIO.BCM)

    # Inputs: PIR and IR Sensors
    GPIO.setup(PIR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(IR_SENSOR_PIN, GPIO.IN)

    # Inputs/Outputs: Ultrasonic Sensor
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    # Ensure the trigger pin is low initially
    GPIO.output(TRIG_PIN, GPIO.LOW)
    
    # Output: Buzzer
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.LOW) # Buzzer off initially
    
    print("GPIO setup complete. All sensors and buzzer initialized.")


def pir_motion_detection(pin):
    """Callback function executed when the PIR sensor detects motion (non-blocking)."""
    if GPIO.input(pin):
        print(f"[{time.strftime('%H:%M:%S')}] >>> MOTION DETECTED (PIR Pin {pin})!")


def get_distance():
    """Measures the distance using the Ultrasonic Sensor (HC-SR04)."""
    # 1. Send 10us pulse to trigger pin
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, GPIO.LOW)

    pulse_start_time = time.time()
    pulse_end_time = time.time()

    # 2. Measure the time until the echo pin goes HIGH (pulse start)
    # Added a timeout to prevent infinite loops if the sensor fails to respond
    timeout_start = time.time()
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        pulse_start_time = time.time()
        if time.time() - timeout_start > 0.04: # 40ms timeout
            return -1 # Indicate a failure or out of range
        
    # 3. Measure the time until the echo pin goes LOW (pulse end)
    timeout_start = time.time()
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        pulse_end_time = time.time()
        if time.time() - timeout_start > 0.04: # 40ms timeout
            return -1 # Indicate a failure or out of range

    # 4. Calculate distance
    pulse_duration = pulse_end_time - pulse_start_time
    
    # Distance = Time * Speed of Sound (divided by 2 because it's round trip)
    distance = (pulse_duration * SPEED_OF_SOUND) / 2
    
    # Limit to reasonable range
    if distance > 400:
        return 400
        
    return round(distance, 2)


def buzz(duration=0.1):
    """Activates the buzzer for a short duration."""
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(BUZZER_PIN, GPIO.LOW)


def main_loop():
    """The main detection loop for continuous monitoring of all sensors."""
    try:
        # PIR Sensor: Use Event Detection (non-blocking)
        GPIO.add_event_detect(PIR_SENSOR_PIN, GPIO.RISING, callback=pir_motion_detection, bouncetime=500)
        print("\n--- PIR Motion Sensor (GPIO 17) is Active ---")
        
        # Main polling loop
        while True:
            # 1. IR Sensor Check (Polling)
            ir_state = GPIO.input(IR_SENSOR_PIN)
            if ir_state == GPIO.LOW:
                print(f"[{time.strftime('%H:%M:%S')}] *** OBSTACLE DETECTED *** (IR Pin {IR_SENSOR_PIN})")
            
            # 2. Ultrasonic Sensor Check
            distance_cm = get_distance()
            
            if distance_cm > 0:
                print(f"[{time.strftime('%H:%M:%S')}] Distance: {distance_cm:0.2f} cm")

                if distance_cm < DISTANCE_THRESHOLD:
                    print(f"[{time.strftime('%H:%M:%S')}] !!! WARNING: Too Close ({distance_cm:0.2f} cm)! Buzzing...")
                    buzz(0.2) # Activate buzzer
                else:
                    # Give the buzzer a break if it was previously on
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Distance reading failed or out of range.")
                
            # Wait a short period before checking again
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nExiting program...")
    
    finally:
        # Ensure all GPIO is cleaned up
        GPIO.cleanup()
        print("GPIO cleanup complete.")

if __name__ == '__main__':
    setup()
    main_loop()
