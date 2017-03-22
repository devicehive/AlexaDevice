#!/usr/bin/env python3

import os

LOCAL_HOST="alexa.local"
LOCAL_PORT=3000
BASE_URL = "http://" + LOCAL_HOST + ":" + str(LOCAL_PORT) + "/"
DEFAULT_VOICE_THRESHOLD = 0.25
DEFAULT_PRODUCT_ID = ""
DEFAULT_CLIEND_ID = ""
DEFAULT_DEVICE_SERIAL = ""
DEFAULT_CLIENT_SECRET = ""
ALEXA_CREDENTIALS_FILE = os.getenv("SNAP_USER_DATA", ".") + "/alexa_credentials"
