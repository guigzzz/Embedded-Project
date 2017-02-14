import machine
import ustruct as struct
import time
import network
from umqtt.simple import MQTTClient
import ujson
import math

# assign register adresses for I2C connections
COMMAND = 0x80
PROXIMITYRATE = 0x82
LIGHTSENSORRATE = 0x84
PROXIMITYDATA = 0x87
LIGHTSENSORDATA = 0x85
SLAVEADDRPROX = 19
SLAVEADDRTEMP = 64
HUMD = b'\xF5'
TEMP = b'\xF3'

# disable board hotspot
ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)

# assign connection parameters of I2C
i2c = machine.I2C(machine.Pin(5), machine.Pin(4))
# enable periodic prox measurement
i2c.writeto_mem(SLAVEADDRPROX, COMMAND, b'\x07')
time.sleep(0.1)
# set light measurement rate to 7sample/sec
i2c.writeto_mem(SLAVEADDRPROX, PROXIMITYRATE, b'\x02')
time.sleep(0.1)
i2c.writeto_mem(SLAVEADDRPROX, LIGHTSENSORRATE, b'\x07')
time.sleep(0.1)


# set p12 to PWM output
p12 = machine.Pin(12)
pwm12 = machine.PWM(p12)
pwm12.freq(500)		# initialise frequency
pwm12.duty(0)		# initialise duty cycle


led_duty = 0
target = 1900		# initialise light inensity target
day_time = True     # initialise day/night bool

# establish MQTT connection and subscribing to topics
def connect_to_broker():
	# scan for all available networks
	print("attempting to connect to broker network...")
	wlan = network.WLAN(network.STA_IF)
	nets = [net[0] for net in wlan.scan()]

	# connect to EEERover
	if b'EEERover' in nets:
		wlan.connect("EEERover", "exhibition")
		while not wlan.isconnected():
		    pass

		client = MQTTClient(machine.unique_id(), "192.168.0.10")
		client.connect()
		print("broker network found and connected")
		client.set_callback(sub_cb)					# set callback function to process msg from MQTT
		client.subscribe("esys/time")				# subscribe to time topic
		client.subscribe("esys/PNL/config")			# subscribe to user configuration topic
		
		print("subscribed to broker")
		return client

	print("broker network not found")
	return None

def sub_cb(topic, msg):
	global target,day_time			# one variable declared by topic
	print("handling callback:")
	print(topic)
	print(msg)
	topic = str(topic,'utf-8')		# decode topic from MQTT
	msg = str(msg,'utf-8')			# decode msg from MQTT
	if topic == "esys/time":								# TIME TOPIC
		msg = ujson.loads(msg)
		timestr = msg["date"]	
		hour = int(timestr[11:12]) + int(timestr[20:21]);		# decode hourly time
		if (hour<4 or hour>23):									# sleep mode between 11:00pm and 4:00am
			day_time = True
		else:
			day_time = True
	elif topic == "esys/PNL/config":						# CONFIG TOPIC
		msg = ujson.loads(msg)
		target = msg["target"]									# set target according to msg
		#print(target)

# convert incoming byte array from i2c bus 
def convert(bytes):
    (bytes,) = struct.unpack('>h', bytes)
    return bytes

# read and return light sensing data
def getamb():
    amb = i2c.readfrom_mem(SLAVEADDRPROX, LIGHTSENSORDATA, 2)
    return convert(amb)					# convert to lux

# read and return humidity/temperature sensing data
def gethumdandtemp():
    i2c.writeto(SLAVEADDRTEMP, HUMD)
    time.sleep(0.05)
    humd = i2c.readfrom(SLAVEADDRTEMP, 2)
    time.sleep(0.05)
    i2c.writeto(SLAVEADDRTEMP, TEMP)
    time.sleep(0.05)
    temp = i2c.readfrom(SLAVEADDRTEMP, 2)

    humd = (125 * convert(humd)) / 65536 - 6			# convert to percentages (%)
    temp = (175.72 * convert(temp)) / 65536 - 46.85		# convert to degrees (C)

    return [humd, temp]

# variable duty_cycle increase/decrease step size to improve system's reactivity
def step_size(target, light_sense):
	step = ((target-light_sense)/16383)*800		# evaluate, normalise and scale target vs. sensing difference
	step = math.floor(step)
	return int(math.fabs(step))					# return step tailored step size


# feedback control system regulating the LED's dutycycle
def dutycycle_monitor(target, light_sense, led_duty):
    step = step_size(target, light_sense)
    if (light_sense < target) & (led_duty < 1024-step):
        led_duty += step
    elif (light_sense > target) & (led_duty > step):
        led_duty -= step
    return led_duty


# setup connection and subscribtion
client = connect_to_broker()

# main loop
if client == None:
    while 1:
        # measure prox,amb data
        amb = getamb()
        # measure temp,humidity data
        [humd, temp] = gethumdandtemp()

        # measures and sets required duty cycle
        led_duty = dutycycle_monitor(target, amb, led_duty)
        pwm12.duty(led_duty)

        print('{"Ambient Light":' + str(amb) + ',"Humidity":' + str(
            humd) + ',"Temperature":' + str(temp) + ',"Led Duty Cycle":' + str(led_duty) + '}')


else:
    while 1:
    	if day_time == True:
	        for i in range(100):
	            amb = getproxandamb()
	            # measure temp,humidity data
	            [humd, temp] = gethumdandtemp()

	            # measures and sets required duty cycle
	            led_duty = dutycycle_monitor(target, amb, led_duty)
	            pwm12.duty(led_duty)
	            #if i%20==0:
	            	#client.connect()
	            client.check_msg()
	            	#client.disconnect()

	        jsonstr = '{"Ambient Light":' + str(amb) + ',"Humidity":' + str(
	            humd) + ',"Temperature":' + str(temp) + ',"Led Duty Cycle":' + str(led_duty) + '}'

	        print(jsonstr)
	        print(target)
	        #client.connect()
        	client.publish("esys/PNL",jsonstr)
        	#client.disconnect()
        else:
        	for i in range(100):
        		[humd, temp] = gethumdandtemp()
        		#if i%20==0:
        			#client.connect()
        		client.check_msg()
        			#client.disconnect()
        		
        	jsonstr = '{"Humidity":' + str(humd) + ',"Temperature":' + str(temp) + ',"Led Duty Cycle":' + str(led_duty) + '}'
        	print(jsonstr)
        	#client.connect()
        	client.publish("esys/PNL",jsonstr)
        	#client.disconnect()

# end main