import paho.mqtt.client as mqtt  #import the client1
import time
import json

broker_address="192.168.0.10"
client = mqtt.Client("P1")  

client.connect(broker_address)      #connect to broker

print("input 0 to quit")
target = input("input target light value:\n")

while target!="0":
	jsonstr = '{"target":' + str(target) + '}'
	client.publish("esys\\PNL\\config",jsonstr)
	target = input("input target light value\n")

