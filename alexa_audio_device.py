#!/usr/bin/env python3

pulse = None

def init():
	global pulse
	try:
		import alexa_audio_device_pulse
		pulse = alexa_audio_device_pulse.pulse_init()
	except (ImportError, OSError):
		pass

def cleanup():
	if pulse:
		import alexa_audio_device_pulse
		alexa_audio_device_pulse.cleanup(pulse)

def get_audio_device(macAddress):
	global cleanupMethod
	if macAddress:
		import alexa_audio_bt
		return alexa_audio_bt.BluetoothAudio(macAddress)
	else:
		if pulse:
			import alexa_audio_device_pulse
			return alexa_audio_device_pulse.AlexaAudioDevice(pulse)
		else:
			import alexa_audio_device_pyaduio
			return alexa_audio_device_pyaduio.AlexaAudioDevice()

