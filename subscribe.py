
#requires paho library
#code to be run on a laptop
#subscribes to a topic and reads from it

import paho.mqtt.client as mqtt  #import the client1
import time

import matplotlib.pyplot as plt
    
def on_message(client1, userdata, message):
    print("message received  "  ,str(message.payload.decode("utf-8")))

broker_address="192.168.0.10"
client1 = mqtt.Client("P1")    #create new instance
client1.on_message= on_message        #attach function to callback
time.sleep(1)
client1.connect(broker_address)      #connect to broker
client1.loop_start()    #start the loop
client1.subscribe("esys/time")
time.sleep(100)
client1.disconnect()
client1.loop_stop()
