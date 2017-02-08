
#to be run on the esp8266
#connects to broker wifi
#continuously sends data to the broker 

import machine
from umqtt.simple import MQTTClient
import time
import network

wlan = network.WLAN(network.STA_IF)
wlan.connect("EEERover","exhibition")
while !wlan.isconnected():
	time.sleep(1)

client = MQTTClient(machine.unique_id(),"192.168.0.10")
client.connect()
while 1:
	client.publish("PNL",bytes("Travis Scott Fell In a Hole",'utf-8'))
	time.sleep(2)
