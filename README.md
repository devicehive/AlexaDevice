# Alexa Device
This project allows to launch Alexa on any Linux devices, even on embedded devices like Raspberry Pi (with usb headset).

# Running
* Follow this manual to create your own device and security profile - https://github.com/alexa/alexa-avs-sample-app/wiki/Create-Security-Profile  
Add `http://alexa.local:3000/authresponse` to `Allowed Return URLs` and `http://alexa.local:3000` to `Allowed Origins`
_Note this step can be skipped if you already have device profile credentials._
* Install dependencies
```bash
sudo apt install ffmpeg swig libportaudio2 libpulse-dev
sudo pip3 install h2 hpack hyper hyperframe requests 'git+https://github.com/moaxey/python-zeroconf' pocketsphinx pyaudio
```
_Note 'libpulse-dev' should be installed only for PulseAudio based devices. 'pyaduio' and 'libportaudio2' should be installed on other devices, for example alsa capable_
* Make sure your system has PulseAudio support.
* Run
```bash
python3 alexa.py
```
* Open http://alexa.local:3000 in web browser on local device or device in the same network.
_Note app provides mDNS advertisement of local domain alexa.local. This is very helpful for using with monitorless devices._
* Fill device credentials which was created in step 1, click 'log in'.
_Note Voice detection threshold is float value for adjusting voice detection. The less value, the easier to trigger. You may need to adjust it for your mic and voice._
* Fill your amazon credentials.
* Now you can speak with Alexa. App uses voice activation. Say 'Alexa' and phrase that you want to say to her. App makes beep in speakers when it hear 'Alexa' keyword and start recording.

# Snap package ( https://www.ubuntu.com/desktop/snappy )
App can be built as snap package.
Install `pulseaudio` snap before installing this:
```bash
sudo snap install --devmode pulseaudio
```
Now build and install:
```bash
cd snap
snacraft
sudo snap install --devmode alexa_1.0_amd64.snap
sudo snap connect alexa:alsa :alsa
```
_Note last line should be ran only for alsa based devices_

# 3rd party parts in source code
Modified Python Alexa Voice Service - https://github.com/nicholasjconn/python-alexa-voice-service  
For license details, see LICENSE file.
