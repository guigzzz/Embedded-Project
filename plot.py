import matplotlib.pyplot as plt
import json
import numpy as np

f = open('data.txt')
lines = f.readlines()
f.close()



proximity = []
ambient_light = []
humidity = []
temperature = []
led_duty = []

for line in lines:
	print(line)
	data = json.loads(line)
	proximity.append(data["Proximity"])
	ambient_light.append(data["Ambient Light"])
	humidity.append(data["Humidity"])
	temperature.append(data["Temperature"])
	led_duty.append(data["Led Duty Cycle"])
	

	
numlines = len(lines)
t = np.arange(0.,numlines)
plt.figure(1);
prox, = plt.plot(t,proximity)
amb, = plt.plot(t,ambient_light)
humd, = plt.plot(t,humidity)
temp, = plt.plot(t,temperature)
duty, = plt.plot(t,led_duty)
plt.legend([prox,amb,duty],['proximity','ambient light','led duty cycle'])
plt.figure(2);
humd, = plt.plot(t,humidity)
temp, = plt.plot(t,temperature)
plt.legend([humd,temp],['humidity','temperature'])
plt.show()


