#!/usr/bin/env python3

import threading
import math
import struct
import time
import alexa_audio_device
from subprocess import Popen, PIPE, STDOUT
from pocketsphinx import *

DETECT_HYSTERESIS = 1.2 # level should fall lower that background noise
DETECT_MIN_LENGTH_S = 2.5 # minimal length of record
DETECT_MAX_LENGTH_S = 10 # minimal amount of buffers to activate

class AlexaAudio:
	def __init__(self, threshold, callback):
		self.ad = alexa_audio_device.AlexaAudioDevice()
		self.callback = callback
		self.beep_buf = self._beep()
		self.is_run = True
		self.average = 100.0
		self.skip = 0
		# init pocketsphinx
		config = Decoder.default_config()
		config.set_string('-hmm', os.path.join(get_model_path(), 'en-us'))
		config.set_string('-dict', os.path.join(get_model_path(), 'cmudict-en-us.dict'))
		config.set_string('-logfn', '/dev/null')
		config.set_string('-keyphrase', 'alexa')
		print("Voice threshold is " + str(threshold))
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

	def beep(self):
		self.play(self.beep_buf)

	def start_capture(self, notify = True):
		self.beep()
		self.capture_in_progress = True
		self.detectBuffer = bytes()
		self.notify = notify

	def processAudio(self):
		print("Audio Processing started.")
		while self.is_run:
			buf = self.ad.read(16000)
			if buf is None:
				print("Alexa audio processing exit")
				break
			if self.skip > 0:
				self.skip -= len(buf)
				continue
			level = 0
			for i in range(0, len(buf), 2):
				val = struct.unpack_from('<h', buf, i)[0] # 16 bit little endian
				level += abs(val)
			level = level / len(buf) / 2

			if self.capture_in_progress:
				self.detectBuffer += buf
				duration = len(self.detectBuffer)/16000/2
				if duration >= DETECT_MAX_LENGTH_S or (
					duration >= DETECT_MIN_LENGTH_S and 
					level * DETECT_HYSTERESIS < self.average):
					self.capture_in_progress = False
					print("Finished " + str(level) + "/" + str(self.average) + " "
						+ str(duration) + "s")
					self.buffer = self.detectBuffer
					if self.notify:
						threading.Thread(target=self.callback).start()
						self.skip += 16000
					#self.play(self.detectBuffer)
			else:
				self.decoder.process_raw(buf, False, False)
				if self.decoder.hyp() != None:
					self.start_capture()
					self.detectBuffer += buf
					print("Found Alexa keyword")
					self.decoder.end_utt()
					self.decoder.start_utt()
				else:
					self.average = (self.average + level) / 2
		print("Audio Processing finished.")

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
		res = self.buffer
		self.buffer = None
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

	def play_wav(self, file, timeout=None, stop_event=None, repeat=False):
		# TODO
		print("play_wav " + file)

