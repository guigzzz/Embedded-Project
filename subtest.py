import network
from umqtt.simple import MQTTClient
import time
import machine



def sub_cb(topic,msg):
	print((topic,msg))		
	
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
	client.subscribe("esys\\PNL\\config")
	client.subscribe("esys\\time")
	
while 1:
	client.check_msg()
	time.sleep(1)
	
