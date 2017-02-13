#!/usr/bin/env python3

import json
import alexa_params
import alexa_device

alexa = None

def start():
	global alexa
	if alexa is not None:
		return
	try:
		with open(alexa_params.ALEXA_CREDENTIALS_FILE, 'r') as infile:
			alexa_config = json.load(infile)
		print("Alexa found config.")
		alexa = alexa_device.AlexaDevice(alexa_config)
	except IOError:
		pass

def close():
	global alexa
	if alexa is not None:
		alexa.close()
		alexa = None

def main():
	start()
	if alexa is not None:
		try:
			input("Alexa started. Press Enter to exit...\n")
		except KeyboardInterrupt:
			pass
		alexa.close()
 
if __name__ == '__main__':
	main()
