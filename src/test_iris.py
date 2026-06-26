import Jetson.GPIO as GPIO
import time

PWM0 = 32
PWM1 = 33
DUTY0 = 60
DUTY1 = DUTY0

GPIO.setmode(GPIO.BOARD)

GPIO.setup(PWM0, GPIO.OUT)


pwm0 = GPIO.PWM(PWM0, 1000)


print("Starting PWM0")
pwm0.start(70)

time.sleep(0.1)

print("Starting PWM1")
GPIO.setup(PWM1, GPIO.OUT)
pwm1 = GPIO.PWM(PWM1, 1000)
pwm1.start(70)

time.sleep(1000)

pwm0.stop()
pwm1.stop()
GPIO.cleanup()
