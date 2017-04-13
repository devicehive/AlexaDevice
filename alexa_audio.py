#!/usr/bin/env python3

import threading
import math
import struct
import time
import alexa_audio_device
import logging
from subprocess import Popen, PIPE, STDOUT
from pocketsphinx import *

DETECT_HYSTERESIS = 1.2 # level should fall lower that background noise
DETECT_MIN_LENGTH_S = 2.5 # minimal length of record
DETECT_MAX_LENGTH_S = 10 # minimal amount of buffers to activate
DETECT_BUFFERS_FOR_INIT = 5 # number of buffers for initialising

class AlexaAudio:
	def __init__(self, threshold, deviceMac, callback):
		self.ad = alexa_audio_device.get_audio_device(deviceMac)
		self.callback = callback
		self.beep_finished_buf = self._beep(150, 1000)
		self.beep_short_buf = self._beep(150, 3000)
		self.beep_failed_buf = self._beep(600, 400)
		self.is_run = True
		self.average = 100.0
		self.init_counter = 0
		self.skip = 0
		# init pocketsphinx
		config = Decoder.default_config()
		config.set_string('-hmm', os.path.join(get_model_path(), 'en-us'))
		config.set_string('-dict', os.path.join(get_model_path(), 'cmudict-en-us.dict'))
		config.set_string('-logfn', '/dev/null')
		config.set_string('-keyphrase', 'alexa')
		logging.info("Voice threshold is " + str(threshold))
		config.set_float('-kws_threshold', threshold)
		self.decoder = Decoder(config)
		self.decoder.start_utt()
		self.capture_in_progress = False
		self.buffer = None
		self.notify = True
		self.pt = threading.Thread(target=self.processAudio)
		self.pt.start()

	def _beep(self, length_ms = 150, frequency = 1000.0, framerate = 16000, amplitude = 0.2):
		period = int(framerate / frequency)
		snd = bytes()
		for i in range(0, int(framerate * length_ms / 1000)):
			val = 32767.0 * amplitude * math.sin(2.0 * math.pi * float(i % period) / period)
			snd += struct.pack('<h', int(val))
		return snd

	def beep_finished(self):
		self.play(self.beep_finished_buf)
		self.ad.flush()

	def beep_short(self):
		self.play(self.beep_short_buf)
		self.ad.flush()

	def beep_failed(self):
		self.play(self.beep_failed_buf)
		self.ad.flush()

	def start_capture(self, notify = True):
		self.beep_short()
		self.capture_in_progress = True
		self.detect_buffer = bytes()
		self.detect_buffer_max = 0
		self.notify = notify

	def processAudio(self):
		logging.info("Audio Processing started.")
		while self.is_run:
			buf = self.ad.read(16000)
			if buf is None:
				time.sleep(0.5)
				continue
			if self.skip > 0:
				self.skip -= len(buf)
				continue
			level = 0
			for i in range(0, len(buf), 2):
				val = struct.unpack_from('<h', buf, i)[0] # 16 bit little endian
				level += abs(val)
			level = level / (len(buf) / 2)

			if self.capture_in_progress:
				self.detect_buffer += buf
				if level > self.detect_buffer_max:
					self.detect_buffer_max = level
				duration = len(self.detect_buffer)/16000/2
				if duration >= DETECT_MAX_LENGTH_S or (
					duration >= DETECT_MIN_LENGTH_S and 
					level < self.average * DETECT_HYSTERESIS):
					self.capture_in_progress = False
					if self.detect_buffer_max > self.average * DETECT_HYSTERESIS:
						logging.info("Finished " + str(duration) + "s")
						self.buffer = self.detect_buffer
						if self.notify:
							threading.Thread(target=self.callback).start()
							self.skip += 16000
						#self.play(self.detect_buffer)
					else:
						logging.info("Cancel " + str(duration) + "s due to the low level ")
						#self.beep_failed()
			else:
				self.decoder.process_raw(buf, False, False)
				if self.decoder.hyp() != None and self.init_counter > DETECT_BUFFERS_FOR_INIT:
					self.start_capture()
					self.detect_buffer += buf
					logging.info("Found Alexa keyword")
					self.decoder.end_utt()
					self.decoder.start_utt()
				else:
					if self.init_counter <= DETECT_BUFFERS_FOR_INIT:
						if self.init_counter == DETECT_BUFFERS_FOR_INIT:
							logging.info("Alexa is initialized and started.")
						self.init_counter += 1
					self.average = self.average * 0.75 + level * 0.25
		logging.info("Audio Processing finished.")

	def close(self):
		self.is_run = False
		self.pt.join()
		self.ad.close()

	def get_audio(self, timeout = None):
		if timeout is not None:
			self.start_capture(False)
			for i in range(int(timeout)):
				if(self.buffer is not None):
					break
				time.sleep(1)
			if self.buffer is None:
				if self.detect_buffer_max > self.average * DETECT_HYSTERESIS:
					res = self.detect_buffer
					self.capture_in_progress = False
					logging.info('Timeout exceed, phrase might not be completed')
					self.beep_finished()
					return res
				else:
					logging.info('Timeout exceed, but nothing was detected')
					self.beep_failed()
					return None
		res = self.buffer
		self.buffer = None
		if res is not None:
			self.beep_finished()
		return res

	def play(self, audio):
		self.skip += len(audio)
		self.ad.write(audio)

	def play_mp3(self, raw_audio):
		p = Popen(['ffmpeg', '-i', '-', '-ac', '1', '-acodec', 
			'pcm_s16le', '-ar', '16000', '-f', 's16le', '-'],
			stdout=PIPE, stdin=PIPE, stderr=PIPE)
		pcm = p.communicate(input=raw_audio)[0]
		self.play(pcm)

