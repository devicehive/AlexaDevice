#!/usr/bin/env python3

import logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', 		datefmt='%d/%m/%Y %H:%M:%S')
logging.getLogger("requests").setLevel(logging.CRITICAL)

import alexa_auth
import alexa_audio_device

def main():
	alexa_audio_device.init()
	alexa_auth.start()
	try:
		input("Press Enter to exit...\n")
	except KeyboardInterrupt:
		pass
	alexa_auth.close()
	alexa_audio_device.cleanup()
 
if __name__ == '__main__':
	main()
