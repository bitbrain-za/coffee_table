#!/usr/bin/env python

from mqtt import MQTT
from rfid import RFID
import threading
import time
import secrets
import logging
from logging.handlers import RotatingFileHandler

formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
# handler = logging.FileHandler(filename='/home/pi/coffee_table.log', mode='w')

handler = RotatingFileHandler(filename='/home/pi/coffee_table.log', mode='a', maxBytes=20*1024*1024, backupCount=2, encoding=None, delay=0)

handler.setFormatter(formatter)
logger = logging.getLogger("coffee_table")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

logger.debug("Starting coordinator Service")

_mqtt_client = MQTT(secrets.mqtt_broker, secrets.mqtt_port, secrets.mqtt_user, secrets.mqtt_pass, logger)
_mqtt_client.start()

while _mqtt_client.connected != True:
    time.sleep(0.1)

_mqtt_client.send_message("buttons", "Running");
_mqtt_client.on_command =  lambda self, command: _mqtt_client.send_message("buttons", command)

_reader = RFID(logger)
_reader.on_tag =  lambda self, tag: _mqtt_client.send_message("tags", tag)
_reader.start()

try:
  while True:
  	time.sleep(1)

except KeyboardInterrupt:
  _reader.stop()
  _mqtt_client.stop()

  self._easy_log(logging.INFO, "App closing")
