Code content for climate monitoring and control:
main program calls upon MQTT protocol functions (subscribe etc.)

Monitoring: main program reads sensing values and converts data to standard units for the user and sends the info to the MQTT broker. 
Control: user inputs a target for greenhouse light intensity from a remote device. Through the broker, the main reads the input and regulates light intensity using an LED, located near the ambient light sensor in order to converge towards the target conditions.

output and demo results are also available

