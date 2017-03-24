#!/usr/bin/env python3
import alexa_params
import alexa_control
import alexa_http_config
import socket
import threading
import logging
from zeroconf import raw_input, ServiceInfo, Zeroconf
from http.server import HTTPServer

localHTTP = None
zeroconf = None
info = None

def get_local_address():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("www.amazon.com", 80))
	res = s.getsockname()[0]
	s.close()
	return res

def start():
	global localHTTP, zeroconf, info, httpthread
	ip = get_local_address()
	logging.info("Local IP is " + ip)

	desc = {'version': '0.1'}
	info = ServiceInfo("_http._tcp.local.",
			"Alexa Device._http._tcp.local.",
			socket.inet_aton(ip), alexa_params.LOCAL_PORT, 0, 0,
			desc, alexa_params.LOCAL_HOST + ".")
	zeroconf = Zeroconf()
	zeroconf.registerService(info)
	logging.info("Local mDNS is started, domain is " + alexa_params.LOCAL_HOST)
	localHTTP = HTTPServer(("", alexa_params.LOCAL_PORT), alexa_http_config.AlexaConfig)
	httpthread = threading.Thread(target=localHTTP.serve_forever)
	httpthread.start()
	logging.info("Local HTTP is " + alexa_params.BASE_URL)
	alexa_control.start()

def close():
	localHTTP.shutdown()
	httpthread.join()
	zeroconf.unregisterService(info)
	zeroconf.close()
	alexa_control.close()

