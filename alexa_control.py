#!/usr/bin/env python3

import os
import json
import logging
import alexa_params
import alexa_device
import alexa_http_config

alexa = None

def start():
	global alexa
	if alexa is not None:
		return
	alexa_config = alexa_http_config.load_config()
	if alexa_config is not None:
		logging.info("Alexa found config.")
		alexa = alexa_device.AlexaDevice(alexa_config)

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
