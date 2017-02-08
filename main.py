import machine
import ustruct as struct
import time
import network
from umqtt.simple import MQTTClient
import ujson

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

target = 1900
led_duty = 0


def connect_to_broker():
    wlan = network.WLAN(network.STA_IF)
    nets = [net[0] for net in wlan.scan()]

    if b'EEERover' in nets:
        wlan.connect("EEERover", "exhibition")
        while not wlan.isconnected():
            time.sleep(0.5)

        client = MQTTClient(machine.unique_id(), "192.168.0.10")
        client.connect()
        print("broker network found and connected")
        return client

    print("broker network not found")
    return None


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

# feedback control system regulating the LED's dutycycle


def dutycycle_monitor(target, light_sense, led_duty):
    if (light_sense < target) & (led_duty < 1024):
        led_duty += 25
    elif (light_sense > target) & (led_duty > 0):
        led_duty -= 25
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

        print('proximity: %d, ambient light: %d, humidity: %d %%, temperature: %d C, duty cycle: %d ' %
              (prox, amb, humd, temp, led_duty))


else:
    while 1:
        for i in range(10):
            [prox, amb] = getproxandamb()
            # measure temp,humidity data
            [humd, temp] = gethumdandtemp()

            # measures and sets required duty cycle
            led_duty = dutycycle_monitor(target, amb, led_duty)
            pwm12.duty(led_duty)

        jsonstr = '{"Proximity":' + str(prox) + ',"Ambient Light":' + str(amb) + ',"Humidity":' + str(
            humd) + ',"Temperature":' + str(temp) + ',"Led Duty Cycle":' + str(led_duty) + '}'

        json = ujson.loads(jsonstr)
        client.publish("PNL",bytes(json))