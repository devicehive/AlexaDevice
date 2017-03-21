#!/usr/bin/env python3

import math
import struct
import ctypes

class _struct_pa_sample_spec(ctypes.Structure):
	_fields_ = [('format', ctypes.c_int),
				('rate', ctypes.c_uint32),
				('channels', ctypes.c_uint8)]
_PA_STREAM_PLAYBACK = 1
_PA_STREAM_RECORD = 2
_PA_SAMPLE_S16LE = 3

def init():
	global pa, in_stream, out_stream, error
	error = ctypes.c_int(0)
	pa = ctypes.cdll.LoadLibrary('libpulse-simple.so.0')
	pa.strerror.restype = ctypes.c_char_p
	ss = _struct_pa_sample_spec(_PA_SAMPLE_S16LE, 16000, 1)

	out_stream = ctypes.c_void_p(pa.pa_simple_new(None,
		'Alexa'.encode('ascii'), _PA_STREAM_PLAYBACK, None,
		'Alexa voice'.encode('ascii'), ctypes.byref(ss),
		None, None, ctypes.byref(error)))
	if not out_stream:
		raise Exception('Could not create pulse audio output stream: '
			+ str(pa.strerror(error), 'ascii'))

	in_stream = ctypes.c_void_p(pa.pa_simple_new(None,
		'Alexa'.encode('ascii'), _PA_STREAM_RECORD, None,
		'Alexa mic'.encode('ascii'), ctypes.byref(ss),
		None, None, ctypes.byref(error)))
	if not in_stream:
		raise Exception('Could not create pulse audio input stream: '
			+ str(pa.strerror(error), 'ascii'))
	print('PulseAudio is initialized.')

def deinit():
	pa.pa_simple_free(in_stream)
	pa.pa_simple_free(out_stream)

class AlexaAudioDevice:
	def __init__(self):
		pa.pa_simple_flush(in_stream)
		pa.pa_simple_flush(out_stream)

	def close(self):
		pa.pa_simple_flush(in_stream)
		pa.pa_simple_flush(out_stream)

	def write(self, b):
		return pa.pa_simple_write(out_stream,	b, len(b), ctypes.byref(error))

	def flush(self):
		pa.pa_simple_flush(out_stream)

	def read(self, n):
		data = ctypes.create_string_buffer(n)
		pa.pa_simple_read(in_stream, data, n, ctypes.byref(error))
		return data.raw

