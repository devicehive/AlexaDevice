#!/usr/bin/env python3

import pyaudio
import math
import struct

class AlexaAudioDevice:
	def __init__(self):
		self.pa = pyaudio.PyAudio()
		self.in_stream = self.pa.open(format=pyaudio.paInt16, channels=1,
						rate=16000, input=True)
		self.in_stream.start_stream()
		self.out_stream = self.pa.open(format=pyaudio.paInt16, channels=1,
						rate=16000,	output=True)
		self.out_stream.start_stream()

	def close(self):
		self.in_stream.close()
		self.out_stream.close()
		self.pa.terminate()

	def write(self, b):
		return self.out_stream.write(b)

	def read(self, n):
		return self.in_stream.read(n)

	def flush(self):
		pass


