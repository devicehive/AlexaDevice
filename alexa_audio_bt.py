#!/usr/bin/env python3

import bluetooth
import logging
import time
import threading
import struct
import sys
import math

# from specs
SOL_BLUETOOTH = 274
SOL_SCO = 17
BT_VOICE = 11
BT_VOICE_TRANSPARENT = 0x0003
BT_VOICE_CVSD_16BIT = 0x0060
SCO_OPTIONS = 1
L2CAP_UUID = "0100"
SCO_HEADERS_SIZE = 16

class BluetoothAudio:
	""" This object connect to Bluetooth handset/nandsfree device
	    stream audio from microphone and to speaker.
	"""
	HFP_TIMEOUT = 1.0
	HFP_CONNECT_AUDIO_TIMEOUT = 10.0
	AUDIO_8KHZ_SIGNED_8BIT_MONO = 0
	AUDIO_16KHZ_SIGNED_16BIT_LE_MONO = 1
	CAPTURE_BUFFER_MAX_SIZE = 16777216 # 16 Mb

	def __init__(self, addr, format = AUDIO_8KHZ_SIGNED_8BIT_MONO):
		""" Create object which connects to bluetooth device in the background.
		    Class automatically reconnects to the device in case of any errors.
		:param addr: MAC address of Bluetooth device, string.
		"""
		self.audio = None
		self.hfp = None
		self.addr = addr
		self.resample = (format == self.AUDIO_16KHZ_SIGNED_16BIT_LE_MONO)
		self.wlt = threading.Thread(target=self._worker_loop)
		self.wlt.start()
		self.buf =  bytes()
		self.rlt = None
		self.rltl = threading.Lock()

	def _read_loop(self):
		logging.info('Read loop start')
		self.buf = bytes()
		while self.rlt:
			try:
				data_8s8b = self.audio.recv(self.sco_payload)
			except bluetooth.btcommon.BluetoothError:
				data_8s8b = None
			if not data_8s8b or len(data_8s8b) == 0:
				self.audio.close()
				self.audio = None
				logging.warning('Capture audio failed')
				break
			if self.resample:
				# convert data
				data = bytes()
				for v in data_8s8b:
					# convert from 8 kHz signed 8 bit to 16 kHz signed 16 bit le
					if v > 127:
						v = v - 256
					v = v * 256
					data += struct.pack('<hh', v, v)
			else:
				data = data_8s8b
			self.rltl.acquire(True)
			if len(self.buf) > self.CAPTURE_BUFFER_MAX_SIZE:
				logging.warning('Capture buffer overflow')
				self.buf = bytes()
			self.buf += data
			self.rltl.release()
		logging.info('Read loop stop')

	def _worker_loop(self):
		logging.info('HFPDevice class is initialised')
		while self.wlt:
			self._find_channel()
			if not self.channel:
				time.sleep(self.HFP_TIMEOUT)
				continue
			logging.info('HSP/HFP found on RFCOMM channel ' + str(self.channel))
			self._connect_service_level()
			if not self.hfp:
				time.sleep(self.HFP_TIMEOUT)
				continue
			try:
				self._parse_channel()
			except bluetooth.btcommon.BluetoothError as e:
				logging.warning('Service level connection disconnected: ' + str(e))
				time.sleep(self.HFP_TIMEOUT)
			self._cleanup()

	def _parse_channel(self):
		audio_time = time.time() + self.HFP_CONNECT_AUDIO_TIMEOUT
		sevice_notice = True
		while self.wlt:
			data = self._read_at()
			if data:
				if b'AT+BRSF=' in data:
					self._send_at(b'+BRSF: 0')
					self._send_ok()
				elif b'AT+CIND=?\r' == data:
					self._send_at(b'+CIND: ("service",(0,1)),("call",(0,1))')
					self._send_ok()
				elif b'AT+CIND?\r' == data:
					self._send_at(b'+CIND: 1,0')
					self._send_ok()
				elif b'AT+CMER=' in data:
					self._send_ok()
					# after this command we can establish audio connection
					sevice_notice = False
					self._connect_audio()
				elif b'AT+CHLD=?\r' == data:
					self._send_at(b'+CHLD: 0')
					self._send_ok()
				else:
					self._send_error()
			# if we don't get service level connection, try audio anyway
			if not self.audio:
				if audio_time < time.time():
					if sevice_notice:
						logging.warning('Service connection timed out, try audio anyway...')
						sevice_notice = False
					self._connect_audio()

	def _connect_service_level(self):
		hfp = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
		try:
			hfp.connect((self.addr, self.channel))
		except bluetooth.btcommon.BluetoothError as e:
			hfp.close()
			logging.warning('Failed to establish service level connection: ' + str(e))
			return
		hfp.settimeout(self.HFP_TIMEOUT)
		logging.info('HSP/HFP service level connection is established')
		self.hfp = hfp

	def _connect_audio(self):
		audio = bluetooth.BluetoothSocket(bluetooth.SCO)
		# socket config
		opt = struct.pack ("H", BT_VOICE_CVSD_16BIT)
		audio.setsockopt(SOL_BLUETOOTH, BT_VOICE, opt)
		try:
			audio.connect((self.addr,))
		except bluetooth.btcommon.BluetoothError as e:
			audio.close()
			logging.info('Failed to establish audio connection: ' + str(e))
			return
		opt = audio.getsockopt(SOL_SCO, SCO_OPTIONS, 2)
		mtu = struct.unpack('H', opt)[0]
		self.audio = audio
		self.sco_payload = mtu - SCO_HEADERS_SIZE
		self.rlt = threading.Thread(target=self._read_loop)
		self.rlt.start()
		logging.info('Audio connection is established, mtu = ' + str(mtu))

	def _find_channel(self):
		# discovery RFCOMM channell, prefer HFP.
		hsp_channel = None
		generic_channel = None
		services = bluetooth.find_service(address=self.addr, uuid=L2CAP_UUID)
		for svc in services:
			for c in svc["service-classes"]:
				service_class = c.lower()
				if bluetooth.HANDSFREE_CLASS.lower() == service_class:
					self.channel = int(svc["port"])
					return
				elif bluetooth.HEADSET_CLASS.lower() == service_class:
					hsp_channel = int(svc["port"])
				elif bluetooth.GENERIC_AUDIO_CLASS.lower() == service_class:
					generic_channel = int(svc["port"])
		if hsp_channel:
			self.channel = hsp_channel
		else:
			self.channel = generic_channel

	def _read_at(self):
		try:
			d = self.hfp.recv(1024)
			logging.debug('> ' + d.decode('utf8'))
			return d
		except bluetooth.btcommon.BluetoothError as e:
			if str(e) != 'timed out':
				raise
			return None

	def _send(self, data):
		logging.debug('< ' + data.decode('utf8').replace('\r\n', ''))
		self.hfp.send(data)

	def _send_at(self, data):
		self._send(b'\r\n' + data + b'\r\n')

	def _send_ok(self):
		self._send_at(b'OK')

	def _send_error(self):
		self._send_at(b'ERROR')

	def _cleanup(self):
		if self.rlt:
			rlt = self.rlt
			self.rlt = None
			rlt.join()
		if self.audio:
			self.audio.close()
		if self.hfp:
			self.hfp.close()
		self.hfp = None
		self.audio = None

	def close(self):
		wlt = self.wlt
		self.wlt = None
		wlt.join()
		self._cleanup()

	def is_connected(self):
		""" Check if headset/handfree device is connected.
		:return: True if connected, False otherwise.
		"""
		return (self.audio != None)

	def flush(self):
		""" Clean up capture buffer
		"""
		self.rltl.acquire(True)
		self.buf = bytes()
		self.rltl.release()

	def read(self, length = None):
		""" Receive audio from bluetooth device. Block until read something.
		:param length: number of bytes(not samples) to read, not more then CAPTURE_BUFFER_MAX_SIZE.
		               If None or 0, all aviliable will be read
		:return: Array with audio data(16 kHz signed 16 bit little endian mono data) or None on error.
		"""
		if not self.rlt:
			return None
		if length == None:
			length = 0
		while len(self.buf) == 0 or len(self.buf) < length:
			if not self.rlt:
				return None
			if not self.rlt.isAlive():
				return None
			s = (length - len(self.buf)) / 8000
			if s <= 0:
				self.rlt.join(0.001)
			else:
				if self.resample:
					s = s / 2
				self.rlt.join(s)
		self.rltl.acquire(True)
		if length == 0:
			data = self.buf
			self.buf = bytes()
		else:
			data = self.buf[0:length]
			self.buf =self.buf[length:]
		self.rltl.release()
		return data

	def write(self, data):
		""" Send audio data to bluetooth device. Blocking.
		:param data: array with audio data.
		:param format: audio fromat, for example AUDIO_8KHZ_SIGNED_8BIT_MONO or AUDIO_16KHZ_SIGNED_16BIT_LE_MONO.
		:return: True on success, False on error.
		"""
		if not self.audio:
			return False
		try:
			if self.resample:
				# convert data
				data_8s8m = bytes()
				for i in range(0, len(data), 4):
					val1, val2 = struct.unpack_from('<hh', data, i) # two samples of signed 16 bit le
					val = round((val1 + val2) / 512) # downsample to 8 kHz and turn into 8 bit
					data_8s8m += struct.pack('b', val)
			else:
				data_8s8m = data
			sent = 0
			while sent < len(data_8s8m):
				ts = data_8s8m[sent:(sent+int(self.sco_payload))]
				if len(ts) < self.sco_payload:
					ts += bytes([0] * (self.sco_payload - len(ts)))
				sent += self.audio.send(ts)
			return True
		except bluetooth.btcommon.BluetoothError:
			return False
		except AttributeError: # 'NoneType' object has no attribute 'send'
			return False

	def beep(self, length_ms = 300, frequency = 1000.0, amplitude = 0.5):
		""" Make a beep sound with specified parameters
		:return: True on success, False on error.
		"""
		fps = 8000
		if self.resample:
			fps = 16000
		logging.info('Beep {} Hz, {} ms'.format(frequency, length_ms))
		period = int(fps / frequency)
		length = int(fps * length_ms / 1000)
		snd = bytes()
		for i in range(0, length):
			val = 32767.0 * amplitude * math.sin(2.0 * math.pi * float(i % period) / period)
			snd += struct.pack('<h', int(val))
		return self.write(snd)


def demo_ring(hf):
	time.sleep(1)
	hf._send_at(b'RING')

def main():
	""" Sample of usage BluetoothAudio.
	    This sample loopback audio from microphone to speaker.
	"""
	logging.basicConfig(level=logging.DEBUG, format='%(message)s')

	if len(sys.argv) == 1:
		print("Please specify device MAC address or 'scan' to scan it.")
		sys.exit(1)
	if sys.argv[1] == 'scan':
		nearby_devices = bluetooth.discover_devices(duration=4,lookup_names=True,
			flush_cache=True, lookup_class=False)
		print(nearby_devices)
		return
	if not bluetooth.is_valid_address(sys.argv[1]):
		print("Wrong device address.")
		return
	hf = BluetoothAudio(sys.argv[1], BluetoothAudio.AUDIO_16KHZ_SIGNED_16BIT_LE_MONO)

	# Make a test RING from headset
	#threading.Thread(target=demo_ring, args=[hf]).start()
	try:
		while not hf.is_connected():
			time.sleep(0.1)
		time.sleep(1.5)
		hf.beep()
		time.sleep(0.5)
		hf.flush()
		while True:
			d = hf.read()
			if d:
				hf.write(d)
			else:
				time.sleep(0.5)
			# generate noise
			#hf.write(bytes(i for i in range(hf.sco_payload)))
	except KeyboardInterrupt:
		pass
	hf.close()
	logging.info('\nExiting...')

if __name__ == '__main__':
	main()

