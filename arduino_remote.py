#########################################################
#                                                       #
#   Note: we load config files but don't use them yet.  #
#   The arudiuno does allow for uploading codes but the #
#   codes currently in use are hardcoded. If new codes  #
#   need to be added, they can be done on init to avoid #
#   needing to change arduino firmware.                 #
#                                                       #
#########################################################

import json
from uart import Comms
import threading
from enum import Enum

CMD_SEND      = 0x04
CMD_STOP      = 0x06
CMD_SEND_CODE = 0x07
CMD_RESET     = 0x08

class Remote:
  def __init__(self, id_number, filename, logger, comms):
    self._logger = logger
    self.id = id_number;
    self.one = [0]*2
    self.zero = [0]*2
    self.header = [0]*2
    self.repeat = [0]*2
    self.repeat_length = 0
    self.uart = comms
    self.release_timer = threading.Timer(0xFFFF, self.release_button)
    self.held = 0xFF
    self.parse_file(filename)

  def parse_file(self, filename):
    try:
      f = open(filename, "r")
    except Exception as err:
      self._logger.error("Remote: Can't open file: %s", err)
      raise

    self._data = json.load(f)
    f.close()

    self.one[0] = self._data["One"]["mark"]
    self.one[1] = self._data["One"]["space"]
    self.zero[0] = self._data["Zero"]["mark"]
    self.zero[1] = self._data["Zero"]["space"]
    self.header[0] = self._data["Header"]["mark"]
    self.header[1] = self._data["Header"]["space"]
    self.pulse_trail = self._data["pulse_trail"]
    self.gap = self._data["Gap"]

    predata = int(self._data["pre_data"], 16)
    self.pre_data_bytes = self._data["pre_data_bytes"]

    self.code_length = self._data["code_length"]
    self.codes = self._data["Keys"]
    try:
      self.repeat[0] = self._data["Repeat"]["mark"]
      self.repeat[1] = self._data["Repeat"]["space"]
      self.repeat_length = len(self.repeat)
    except KeyError:
      self.repeat_length = 0

    self._logger.debug("Remote - Loaded remote")
    print("Remote - Loaded remote")
    for c in self.codes:
      print("Key: "+c["name"])
      print("ID: "+hex(c["id"]))
      print("Code: "+c["code"])

  def get_code(self, key):
    try:
      code = (self._codes[key])[1]
    except KeyError:
      return 0xFF
    return code

  def to_string(self):
    data = (self.pre_data_bytes,
      self.code_length,
      len(self.codes),
      self.header[0],
      self.header[1],
      self.one[0],
      self.one[1],
      self.zero[0],
      self.zero[1],
      self.pulse_trail,
      self.gap,
      self.repeat_length,
      self.repeat[0],
      self.repeat[1])
    string = ",".join(hex(x)[2:] for x in data)
    return string

  def predata_to_string(self):
    return hex(self.predata)[2:]

  def press_button(self, button, presses):
    self.release_timer.cancel()
    self.held = 0xFF
    self.uart.send(CMD_SEND, hex(button.value)[2:] + "," + hex(presses)[2:])

  def hold_button(self, button, duration):
    if(button != self.held):
      self.uart.send(CMD_SEND, hex(button.value)[2:] + "," + "FF")
      self.held = button

    self.release_timer.cancel()
    self.release_timer = threading.Timer(duration, self.release_button)
    self.release_timer.start()

  def release_button(self):
    self.held = 0xFF
    self.uart.send(CMD_STOP, None)

class Key(Enum):
  AMP_POWER = 0x00
  AMP_VOL_UP = 0x01
  AMP_MUTE = 0x02
  AMP_VOL_DOWN = 0x03
  AMP_DVD = 0x04
  AMP_AUX = 0x05
  AMP_CD = 0x06
  AMP_TAPE = 0x07
  AMP_TUNER = 0x08
  AMP_VIDEO1 = 0x09
  AMP_VIDEO2 = 0x0A
  AMP_BASS = 0x0B
  TV_POWER = 0x0C
  TV_VOL_UP = 0x0D
  TV_MUTE = 0x0E
  TV_VOL_DOWN = 0x0F
  TV_PLAY = 0x10
  TV_PAUSE = 0x11
  TV_STOP = 0x12
  TV_UP = 0x13
  TV_DOWN = 0x14
  TV_LEFT = 0x15
  TV_RIGHT = 0x16
  TV_ENTER = 0x17