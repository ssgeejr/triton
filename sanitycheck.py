#sanity check

import RPi.GPIO as GPIO, time

PIN = 18           # BCM numbering
ACTIVE_LEVEL = GPIO.LOW  # LOW if jumper set to LOW-trigger; use GPIO.HIGH for HIGH-trigger

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT, initial=GPIO.HIGH if ACTIVE_LEVEL==GPIO.LOW else GPIO.LOW)

try:
    while True:
        GPIO.output(PIN, ACTIVE_LEVEL)   # relay ON
        time.sleep(2)
        GPIO.output(PIN, GPIO.HIGH if ACTIVE_LEVEL==GPIO.LOW else GPIO.LOW)  # relay OFF
        time.sleep(2)
except KeyboardInterrupt:
    pass
finally:
    GPIO.output(PIN, GPIO.HIGH if ACTIVE_LEVEL==GPIO.LOW else GPIO.LOW)
    GPIO.cleanup()