import secrets
import paho.mqtt.client as mqttClient
import time
import sys
import logging
import urllib.request, urllib.error, urllib.parse
import os
import errno
import fcntl, socket
import threading
import random

class MQTT:

  class Message:
    def __init__(self, topic, text):
      self.topic = topic
      self.text = text

  def __init__(self, broker, port, user, passw, logger):
    self._thread = None
    self._thread_terminate = False
    self.running = False
    self._in_callback_mutex = threading.Lock()
    self._callback_mutex = threading.RLock()
    self._client = mqttClient.Client("CoffeeTable" + format(random.randint(0, 255)))

    self.__sem = threading.Semaphore()
    self.Queue = []
    self.connected = False
    self._logger = None
    self.enable_logger(logger)
    self._subject = "coffee_table/"

    self.wait_for_internet_connection()
    self._easy_log(logging.DEBUG, "Network is up")
     
    self._client.username_pw_set(user, password=passw)
    self._client.reconnect_delay_set(1, 60)
    self._client.on_connect= self.on_connect
    self._client.connect(broker, port=port, keepalive=60)

  def enable_logger(self, logger=None):
    if logger is None:
      if self._logger is not None:
        # Do not replace existing logger
        return
      logger = logging.getLogger(__name__)
    self._logger = logger
    self._client.enable_logger(logger)
    
  def _easy_log(self, level, fmt, *args):
    if self._logger is not None:
      self._logger.log(level, fmt, *args)

  def on_connect(self, client, userdata, flags, rc):
      if rc == 0:
          print("connected")
          self._easy_log(logging.INFO, "Connected to broker")
          self.connected = True
   
      else:
          self._easy_log(logging.WARNING, "Connection failed")

  def on_disconnect(self):
    print("disconnected")
    self._easy_log(logging.WARNING, "Disconnected")
    self.connected = False
    self._client.loop_start()        #start the loop
   
    while self.connected != True:    #Wait for connection
      time.sleep(0.1)

  def wait_for_internet_connection(self):
    while True:
      try:
        urllib.request.urlopen(secrets.server_url,timeout=5)
        self._easy_log(logging.DEBUG, "Waiting for network")
        return
      except urllib.error.URLError:
        pass

  def on_ir_message(self, client, userdata, message):
    with self._callback_mutex:
      if self.on_ir_command:
        with self._in_callback_mutex:
          try:
            self.on_ir_command(message.payload.decode("utf-8"))
          except Exception as err:
            self._logger.error('Caught exception in on_ir_command: %s', err)

  def on_ac_temp_message(self, client, userdata, message):
    with self._callback_mutex:
      if self.on_ac_temp:
        with self._in_callback_mutex:
          try:
            self.on_ac_temp(message.payload.decode("utf-8"))
          except Exception as err:
            self._logger.error('Caught exception in on_ac_temp: %s', err)

  def on_command_rx(self, client, userdata, message):
    with self._callback_mutex:
      if self.on_command:
        with self._in_callback_mutex:
          try:
            self.on_command(message.payload.decode("utf-8"))
          except Exception as err:
            self._logger.error('Caught exception in on_command: %s', err)

  def on_brightness_message(self, client, userdata, message):
    with self._callback_mutex:
      if self.on_light_brightness_update:
        with self._in_callback_mutex:
          try:
            self.on_light_brightness_update(message.payload.decode("utf-8"))
          except Exception as err:
            self._logger.error('Caught exception in on_light_brightness_update: %s', err)

  def on_rgb_message(self, client, userdata, message):
    with self._callback_mutex:
      with self._in_callback_mutex:
        try:
          rgb_string = message.payload.decode("utf-8")
          self._logger.debug("RGB Message: " + rgb_string)
          color = [x.strip() for x in rgb_string.split(',')]
          if len(color) == 3:
            self.on_rgb(color[0], color[1], color[2])
          else:
            self._logger.warn('Invalid RGB values: %s', rgb_string)
        except Exception as err:
          self._logger.error('Caught exception in on_rgb_message: %s', err)

  def send_message(self, topic, content):
    self.__sem.acquire()
    self.Queue.append(self.Message(topic, content))
    self.__sem.release()

  def stop(self):
    self._thread_terminate = True

  def start(self):
    if self._thread is not None:
        return False

    self.running = True
    self._thread_terminate = False
    self._thread = threading.Thread(target=self._loop)
    self._thread.daemon = True
    self._thread.start()

  def _loop(self):
    self._easy_log(logging.DEBUG, "Starting MQTT Service")
    self._client.loop_start()        #start the loop
     
    while self.connected != True:    #Wait for connection
        time.sleep(0.1)

    # Subscriptions:

    self._client.subscribe("coffee_table/ir", qos=0)
    self._client.message_callback_add("coffee_table/ir", self.on_ir_message)
    self._client.subscribe("coffee_table/lights/lounge/brightness", qos=0)
    self._client.message_callback_add("hassio/lights/lounge/brightness", self.on_brightness_message)
    # self._client.publish("coffee_table/tags","Service Started")
    self._client.subscribe("coffee_table/command", qos=0)
    self._client.message_callback_add("coffee_table/command", self.on_command_rx)
    self._client.subscribe("coffee_table/rgb", qos=0)
    self._client.message_callback_add("coffee_table/rgb", self.on_rgb_message)
    # /ac/temp - receives lounge temp changes made in HA
    self._client.subscribe("coffee_table/ac/temp", qos=0)
    self._client.message_callback_add("coffee_table/ac/temp", self.on_ac_temp_message)

    while not self._thread_terminate:
      self.__sem.acquire()
      if(len(self.Queue) > 0):
        for m in self.Queue:
          subject = self._subject + m.topic
          print("Sending subject: " + subject + " message: " + m.text)
          self._easy_log(logging.DEBUG, "Sending subject: " + subject + " message: " + m.text + "\n")
          self._client.publish(subject, m.text)
          del self.Queue[:]
        self.__sem.release()
      else:
        self.__sem.release()
      time.sleep(0.1)

    self._client.disconnect()
    self._client.loop_stop()
    self._easy_log(logging.INFO, "Task ended")
    self.running = False

  @property
  def on_ir_command(self):
    return self._on_ir_command

  @on_ir_command.setter
  def on_ir_command(self, func):
    with self._callback_mutex:
      self._on_ir_command = func

  @property
  def on_light_brightness_update(self):
    return self._on_light_brightness_update

  @on_light_brightness_update.setter
  def on_light_brightness_update(self, func):
    with self._callback_mutex:
      self._on_light_brightness_update = func

  @property
  def on_rgb(self):
    return self._on_rgb

  @on_rgb.setter
  def on_rgb(self, func):
    with self._callback_mutex:
      self._on_rgb = func

  @property
  def on_command(self):
    return self._on_command

  @on_command.setter
  def on_command(self, func):
    with self._callback_mutex:
      self._on_command = func

  @property
  def on_ac_temp(self):
    return self._on_ac_temp

  @on_ac_temp.setter
  def on_ac_temp(self, func):
    with self._callback_mutex:
      self._on_ac_temp = func