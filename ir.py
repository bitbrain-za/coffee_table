from gpiozero import LED
from signal import pause
import json
import pigpio
import time

class IR:
  def __init__(self, logger):
    self._thread = None
    self._thread_terminate = False
    self.running = False

    self._logger = logger

    self._logger.debug("Starting IR service")

    self.GPIO       = 14
    self.FILE       = "kenwood_rc_r0630e"
    # FILE       = "test"
    self.FREQ       = 38.0
    self.GAP_MS     = 100
    self.GAP_S      = GAP_MS  / 1000.0

    self.last_tick = 0
    self.in_code = False
    self.code = []
    self.fetching_code = False

    self.ir = LED(self.GPIO)

    self.last_tick = 0
    self.in_code = False
    self.code = []
    self.fetching_code = False