import machine
import ustruct as struct
import time
import network
from umqtt.simple import MQTTClient
import ujson
import math

COMMAND = 0x80
PROXIMITYRATE = 0x82
LIGHTSENSORRATE = 0x84
PROXIMITYDATA = 0x87
LIGHTSENSORDATA = 0x85
SLAVEADDRPROX = 19
SLAVEADDRTEMP = 64
HUMD = b'\xF5'
TEMP = b'\xF3'

ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)

i2c = machine.I2C(machine.Pin(5), machine.Pin(4))
# enable periodic prox measurement
i2c.writeto_mem(SLAVEADDRPROX, COMMAND, b'\x07')
time.sleep(0.1)
# set prox measurement rate to 7sample/sec
i2c.writeto_mem(SLAVEADDRPROX, PROXIMITYRATE, b'\x02')
time.sleep(0.1)
i2c.writeto_mem(SLAVEADDRPROX, LIGHTSENSORRATE, b'\x07')
time.sleep(0.1)

p12 = machine.Pin(12)
pwm12 = machine.PWM(p12)
pwm12.freq(500)
pwm12.duty(0)

global target = 1900
led_duty = 0
global day_time = True


def connect_to_broker():
	print("attempting to connect to broker network...")
	wlan = network.WLAN(network.STA_IF)
	nets = [net[0] for net in wlan.scan()]

	if b'EEERover' in nets:
		wlan.connect("EEERover", "exhibition")
		while not wlan.isconnected():
		    pass

		client = MQTTClient(machine.unique_id(), "192.168.0.10")
		client.connect()
		print("broker network found and connected")
		client.set_callback(sub_cb)
		client.subscribe("esys/time")
		client.subscribe("esys/PNL/config")
		
		print("subscribed to broker")
		return client

	print("broker network not found")
	return None

def sub_cb(topic, msg):
	topic = str(topic,'utf-8')
	msg = str(msg,'utf-8')
	if topic == "esys/time":
		msg = ujson.loads(msg)
		timestr = msg["date"]
		hour = int(timestr[11:12]) + int(timestr[20:21]);
		if (hour<4 or hour>23):
			day_time = False
        else:
            day_time = True
	elif topic == "esys/PNL/config":
		msg = ujson.loads(msg)
		target = msg["target"]


def convert(bytes):
    (bytes,) = struct.unpack('>h', bytes)
    return bytes


def getproxandamb():
    prox = i2c.readfrom_mem(SLAVEADDRPROX, PROXIMITYDATA, 2)
    amb = i2c.readfrom_mem(SLAVEADDRPROX, LIGHTSENSORDATA, 2)
    return [convert(prox), convert(amb)]


def gethumdandtemp():
    i2c.writeto(SLAVEADDRTEMP, HUMD)
    time.sleep(0.05)
    humd = i2c.readfrom(SLAVEADDRTEMP, 2)
    time.sleep(0.05)
    i2c.writeto(SLAVEADDRTEMP, TEMP)
    time.sleep(0.05)
    temp = i2c.readfrom(SLAVEADDRTEMP, 2)

    humd = (125 * convert(humd)) / 65536 - 6
    temp = (175.72 * convert(temp)) / 65536 - 46.85

    return [humd, temp]

def step_size(target, light_sense):
	step = ((target-light_sense)/16383)*800
	step = math.floor(step)
	return int(math.fabs(step))

# feedback control system regulating the LED's dutycycle


def dutycycle_monitor(target, light_sense, led_duty):
    step = step_size(target, light_sense)
    if (light_sense < target) & (led_duty < 1024-step):
        led_duty += step
    elif (light_sense > target) & (led_duty > step):
        led_duty -= step
    return led_duty



client = connect_to_broker()

# main loop
if client == None:
    while 1:
        # measure prox,amb data
        [prox, amb] = getproxandamb()
        # measure temp,humidity data
        [humd, temp] = gethumdandtemp()

        # measures and sets required duty cycle
        led_duty = dutycycle_monitor(target, amb, led_duty)
        pwm12.duty(led_duty)

        print('{"Proximity":' + str(prox) + ',"Ambient Light":' + str(amb) + ',"Humidity":' + str(
            humd) + ',"Temperature":' + str(temp) + ',"Led Duty Cycle":' + str(led_duty) + '}')


else:
    while 1:
    	if day_time == True:
	        for i in range(100):
	            [prox, amb] = getproxandamb()
	            # measure temp,humidity data
	            [humd, temp] = gethumdandtemp()

	            # measures and sets required duty cycle
	            led_duty = dutycycle_monitor(target, amb, led_duty)
	            pwm12.duty(led_duty)

	        jsonstr = '{"Proximity":' + str(prox) + ',"Ambient Light":' + str(amb) + ',"Humidity":' + str(
	            humd) + ',"Temperature":' + str(temp) + ',"Led Duty Cycle":' + str(led_duty) + '}'

	        print(jsonstr)
	        print(target)
	        client.connect()
        	client.publish("esys/PNL",jsonstr)
        	client.check_msg()
        	client.disconnect()
        else:
        	for i in range(100):
        		[humd, temp] = gethumdandtemp()
        		
        	jsonstr = '{"Humidity":' + str(humd) + ',"Temperature":' + str(temp) + ',"Led Duty Cycle":' + str(led_duty) + '}'
        	print(jsonstr)
        	client.connect()
        	client.publish("esys/PNL",jsonstr)
        	client.disconnect()
