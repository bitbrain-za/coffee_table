import paho.mqtt.client as mqttClient
import time
import sys
import logging
import urllib2
import os
import errno
import fcntl, socket
import threading

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
    self._client = mqttClient.Client("CoffeeTable")

    self.__sem = threading.Semaphore()
    self.Queue = []
    self.connected = False
    self.enable_logger(logger);
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
          self._easy_log(logging.INFO, "Connected to broker")
          self.connected = True
   
      else:
          self._easy_log(logging.WARNING, "Connection failed")

  def on_disconnect(self):
    self.connected = False;
    self._client.loop_start()        #start the loop
   
    while self.connected != True:    #Wait for connection
      time.sleep(0.1)

  def wait_for_internet_connection(self):
    while True:
      try:
        response = urllib2.urlopen('https://bitbrain.duckdns.org',timeout=5)
        self._easy_log(logging.DEBUG, "Waiting for network")
        return
      except urllib2.URLError:
        pass

  def on_message(self, client, userdata, message):
    with self._callback_mutex:
      if self.on_command:
        with self._in_callback_mutex:
          try:
            self.on_command(self, message.payload)
          except Exception as err:
            self._logger.error('Caught exception in on_command: %s', err)

  def send_message(self, topic, content):
    self.__sem.acquire()
    self.Queue.append(self.Message(topic, content))
    self.__sem.release()

  def stop(self):
    self._thread_terminate = True;

  def start(self):
    if self._thread is not None:
        return False

    self.running = True;
    self._thread_terminate = False
    self._thread = threading.Thread(target=self._loop)
    self._thread.daemon = True
    self._thread.start()

  def _loop(self):
    self._easy_log(logging.DEBUG, "Starting MQTT Service")
    self._client.loop_start()        #start the loop
     
    while self.connected != True:    #Wait for connection
        time.sleep(0.1)

    self._client.subscribe("coffee_table/commands", qos=1)
    self._client.message_callback_add("coffee_table/commands", self.on_message)
    self._client.publish("coffee_table/tags","Service Started")

    while not self._thread_terminate:
      self.__sem.acquire()
      if(len(self.Queue) > 0):
        for m in self.Queue:
          subject = self._subject + m.topic
          self._easy_log(logging.DEBUG, "Sending subject: " + subject + " message: " + m.text + "\n")
          self._client.publish(subject, m.text);
          del self.Queue[:]
        self.__sem.release()
      else:
        self.__sem.release()
        time.sleep(1)

    self._client.disconnect()
    self._client.loop_stop()
    self._easy_log(logging.INFO, "Task ended")
    self.running = False

  @property
  def on_command(self):
    return self._on_command

  @on_command.setter
  def on_command(self, func):
    with self._callback_mutex:
      self._on_command = func;