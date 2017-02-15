#!/usr/bin/env python3

import alexa_auth

def main():
	alexa_auth.start()
	try:
		input("Alexa started. Press Enter to exit...\n")
	except KeyboardInterrupt:
		pass
	alexa_auth.close()
 
if __name__ == '__main__':
	main()
