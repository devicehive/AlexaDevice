#!/usr/bin/env python3
import os
import alexa_params
import alexa_control
import json
import requests
from http.server import BaseHTTPRequestHandler
from cgi import parse_header
from urllib.parse import parse_qs, urlencode, urlparse

threshold = alexa_params.DEFAULT_VOICE_THRESHOLD
productId = alexa_params.DEFAULT_PRODUCT_ID
clientId = alexa_params.DEFAULT_CLIEND_ID
deviceSerial = alexa_params.DEFAULT_DEVICE_SERIAL
clientSecret = alexa_params.DEFAULT_CLIENT_SECRET
audioDevice = ""

def load_config():
	global clientId, clientSecret, threshold, deviceSerial, productId, audioDevice
	try:
		with open(alexa_params.ALEXA_CREDENTIALS_FILE, 'r') as infile:
			config = json.load(infile)
			clientId = config['Client_ID']
			clientSecret = config['Client_Secret']
			threshold = config['threshold']
			deviceSerial = config['deviceSerial']
			productId = config['productId']
			audioDevice = config['audioDevice']
			return config
	except IOError:
		pass
	return None

class AlexaConfig(BaseHTTPRequestHandler):
	def do_POST(self):
		global threshold
		global productId
		global clientId
		global deviceSerial
		global clientSecret
		global audioDevice
		ctype, pdict = parse_header(self.headers['content-type'])
		if ctype == 'multipart/form-data':
			postvars = parse_multipart(self.rfile, pdict)
		elif ctype == 'application/x-www-form-urlencoded':
			length = int(self.headers['content-length'])
			postvars = parse_qs(self.rfile.read(length), keep_blank_values=1)
		else:
			postvars = {}
		threshold = float(b''.join(postvars.get(bytes("threshold", "utf-8"))).decode("utf-8"))
		productId = b''.join(postvars.get(bytes("productid", "utf-8"))).decode("utf-8")
		clientId = b''.join(postvars.get(bytes("clientid", "utf-8"))).decode("utf-8")
		deviceSerial = b''.join(postvars.get(bytes("serial", "utf-8"))).decode("utf-8")
		clientSecret = b''.join(postvars.get(bytes("secret", "utf-8"))).decode("utf-8")
		audioDevice = b''.join(postvars.get(bytes("audio", "utf-8"))).decode("utf-8")
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		url = "https://www.amazon.com/ap/oa?" + urlencode({
			"client_id": clientId,
			"scope": "alexa:all",
			"scope_data": json.dumps({
				"alexa:all": {
					"productID": productId,
					"productInstanceAttributes": {
						"deviceSerialNumber": deviceSerial
					}
				}
			}).replace(" ", ""),
			"response_type": "code",
			"redirect_uri": alexa_params.BASE_URL + "authresponse"
		})
		self.wfile.write(bytes("<html><head><title>Alexa</title>", "utf-8"))
		self.wfile.write(bytes("<meta http-equiv=\"refresh\" content=\"3; url=" + url + "\"/></head>", "utf-8"))
		self.wfile.write(bytes("<body><p>Redirecting to amazon login service...</p>", "utf-8"))
		self.wfile.write(bytes("</body></html>", "utf-8"))

	def do_GET(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		if self.path.startswith("/authresponse"):
			parsed = urlparse(self.path)
			code = ''.join(parse_qs(parsed.query).get("code"))
			data = {
				"grant_type": "authorization_code",
				"code": code,
				"client_id": clientId,
				"client_secret": clientSecret,
				"redirect_uri": alexa_params.BASE_URL + "authresponse"
			}
			headers = {'Content-Type': 'application/x-www-form-urlencoded'}
			response = requests.post("https://api.amazon.com/auth/o2/token", data=urlencode(data), headers=headers)
			if response.status_code == 200:
				refresh_token = json.loads(response.text)["refresh_token"]
				access_token = json.loads(response.text)["access_token"]
				print("---------Access Token----------------")
				print(access_token)
				print("-------------------------------------")
				with open(alexa_params.ALEXA_CREDENTIALS_FILE, 'w') as outfile:
					data = {
						"threshold": threshold,
						"refresh_token": refresh_token,
						"Client_ID": clientId,
						"Client_Secret": clientSecret,
						"deviceSerial": deviceSerial,
						"productId": productId,
						"audioDevice": audioDevice
					}
					json.dump(data, outfile)
				alexa_control.start()
				self.authorizedAnswer()
			else:
				self.wfile.write(bytes("<html><head><title>Alexa</title>", "utf-8"))
				self.wfile.write(bytes("<body><p>Authorization error. <a href='/'>Click here to try again</a></p>", "utf-8"))
				self.wfile.write(bytes("</body></html>", "utf-8"))
		elif self.path == "/logout":
			try:
				os.remove(alexa_params.ALEXA_CREDENTIALS_FILE)
			except FileNotFoundError:
				pass
			alexa_control.close()
			self.wfile.write(bytes("<html><head><title>Alexa</title>", "utf-8"))
			self.wfile.write(bytes("<meta http-equiv=\"refresh\" content=\"3; url=/\"/></head>", "utf-8"))
			self.wfile.write(bytes("<body><p>Done. Reloading...</p>", "utf-8"))
			self.wfile.write(bytes("</body></html>", "utf-8"))
		elif self.path == "/restart":
			alexa_control.close()
			alexa_control.start()
			self.authorizedAnswer();
		elif os.path.isfile(alexa_params.ALEXA_CREDENTIALS_FILE):
			self.authorizedAnswer();
		else:
			self.wfile.write(bytes("""
				<html><head><title>Alexa</title>
				<style type='text/css'>input[type=text],input[type=password]{width:100%;}input[type=submit]{width:30%;}</style>
				</head><body><form method='post'>
				Voice detection threshold(float value):<br>
				<input type='text' name='threshold' value='""" + str(threshold) + """'><br><br>
				Product ID(Device Type ID):<br>
				<input type='text' name='productid' value='""" + productId + """'><br><br>
				Client ID:<br>
				<input type='text' name='clientid' value='""" + clientId + """'><br><br>
				Device Serial Number:<br>
				<input type='text' name='serial' value='""" + deviceSerial + """'><br><br>
				Client Secret:<br>
				<input type='password' name='secret' value='""" + clientSecret + """'><br><br>
				Bluetooth Audio Device MAC(example 11:22:33:44:55:66, leave empty to use local audio i.e. USB or 3.5mm device):<br>
				<input type='text' name='audio' value='""" + audioDevice + """'><br><br>
				<input type='submit' value='Log in'>
				</form></body></html>
			""", "utf-8"))

	def authorizedAnswer(self):
			self.wfile.write(bytes("<html><head><title>Alexa</title></head>", "utf-8"))
			self.wfile.write(bytes("<body onload=\"if(window.location.pathname.length > 1) window.location.href='" + alexa_params.BASE_URL + "'\"><p>Alexa is configured and started.</p>", "utf-8"))
			self.wfile.write(bytes("<p><a href=/logout>Click here to log out.</a></p>", "utf-8"))
			self.wfile.write(bytes("<p><a href=/restart>Click here to restart Alexa.</a></p>", "utf-8"))
			self.wfile.write(bytes("</body></html>", "utf-8"))

	def log_message(self, format, *args):
        	return

