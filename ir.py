#######################################
#                                     #
#   This has been obsoleted!          #
#   Replaced with arduino_remote.py   #
#   Left here for reference           #
#                                     #
#######################################

# Move to LIRC
# https://www.raspberrypi.org/forums/viewtopic.php?t=235256
# https://raspberrypi.stackexchange.com/questions/70945/setting-up-a-remote-control-using-lirc
# https://www.hackster.io/austin-stanton/creating-a-raspberry-pi-universal-remote-with-lirc-2fd581
# https://www.raspberrypi.org/forums/viewtopic.php?t=236240

from gpiozero import LED
from signal import pause
import json
import pigpio
import time
from config import Config
import threading

class IR:
    def __init__(self, pin, logger):
      self.currently_txing = 0xFF
      self.GPIO       = pin
      # self.FILE       = "/home/pi/app/test"
      self.FILE       = "/home/pi/app/ir_commands"
      self.FREQ       = 38.0
      self.GAP_MS     = 10
      self.GAP_S      = self.GAP_MS  / 1000.0

      self.continuous_tx = False

      self._logger = logger
      self._logger.debug("IR: Starting IR service")

      self.ir = LED(self.GPIO)
      self.emit_time = time.time()

      try:
         f = open(self.FILE, "r")
      except Exception as err:
        self._logger.error("IR: Can't open file: %s", err)
        raise

      self._records = json.load(f)
      f.close()

      self.pi = pigpio.pi() # Connect to Pi.
      if not self.pi.connected:
          raise Exception('IR: Could not connec to pi')

      self.pi.set_mode(self.GPIO, pigpio.OUTPUT) # IR TX connected to this GPIO.
      self.pi.wave_clear()
      self.repeat_timeout = Config.REPEAT_TIMEOUT
      self.stop_timer = threading.Timer(self.repeat_timeout, self.pi.wave_tx_stop)
      self.stop_timer.start() 
      # self.pi.wave_add_new()

      # self._pre_generate_waveforms()

    def _pre_generate_waveforms(self):
      self.waves = {}

      cycle = 1000.0 / self.FREQ

      for x in self._records:

        code = self._records[x]
        wf = []

        for i in range(0, len(code)):
          ci = code[i]
          if i & 1: # Space
            wf.append(pigpio.pulse(0, 0, ci))
          else: # Mark
            cycles = int(round(ci/cycle))
            on = int(round(cycle / 2.0))
            sofar = 0
            for c in range(cycles):
              target = int(round((c+1)*cycle))
              sofar += on
              off = target - sofar
              sofar += off
              wf.append(pigpio.pulse(1<<self.GPIO, 0, on))
              wf.append(pigpio.pulse(0, 1<<self.GPIO, off))
            

        self.pi.wave_add_generic(wf)
        print("New wave: ")
        print("CBS: " + format(self.pi.wave_get_cbs()))
        print("Pulses: " + format(self.pi.wave_get_pulses()))

        self.waves[x] = self.pi.wave_create()

        print(x + " ID: " + format(self.waves[x]))
        self._logger.debug('IR: Loaded code: %s', x)

    # def _pre_generate_waveforms(self):
    #   self.waves = {}

    #   marks_wid = {}
    #   spaces_wid = {}
    #   for x in self._records:

    #     code = self._records[x]
    #     wave = [0]*len(code)

    #     for i in range(0, len(code)):
    #       ci = code[i]
    #       if i & 1: # Space
    #         if ci not in spaces_wid:
    #           self.pi.wave_add_generic([pigpio.pulse(0, 0, ci)])
    #           spaces_wid[ci] = self.pi.wave_create()
    #         wave[i] = spaces_wid[ci]
    #       else: # Mark
    #         if ci not in marks_wid:
    #           wf = self._carrier(self.GPIO, self.FREQ, ci)
    #           self.pi.wave_add_generic(wf)
    #           marks_wid[ci] = self.pi.wave_create()
    #         wave[i] = marks_wid[ci]

    #     self.waves[x] = wave

    #     self._logger.debug('IR: Loaded code: %s', x)

    def __del__(self):
      self.pi.wave_clear()
      self.pi.stop() # Disconnect from Pi.
      self._logger.debug("IR: Closing IR port")

    def send_code(self, code):
      self._tx_wave(self._records[code])
      # self._play_code(self._records[code])

    def amp_power(self):
      self._tx_wave(self._records["AMP_POWER"])

    def amp_aux(self):
      self._tx_wave(self._records["AMP_AUX"])

    def amp_dvd(self):
      self._tx_wave(self._records["AMP_DVD"])

    def amp_video1(self):
      self._tx_wave(self._records["AMP_VDEO1"])

    def amp_video2(self):
      self._tx_wave(self._records["AMP_VDEO2"])

    def amp_6CH(self):
      self._tx_wave(self._records["AMP_6CH"])

    def amp_vol_down(self):
      if self.currently_txing != 0x00:
        self._tx_wave(self._records["AMP_VOL_DOWN"], continuous = True)
        self.currently_txing == 0x00
      self.stop_timer.cancel()
      self.stop_timer = threading.Timer(self.repeat_timeout, self.timeout)
      self.stop_timer.start() 

    def amp_vol_up(self):
      if self.currently_txing != 0x01:
        self._tx_wave(self._records["AMP_VOL_UP"], continuous = True)
        self.currently_txing == 0x01
      self.stop_timer.cancel()
      self.stop_timer = threading.Timer(self.repeat_timeout, self.timeout)
      self.stop_timer.start() 

    def tv_power(self):
      self._tx_wave(self._records["TV_POWER"])

    def tv_play(self):
      self._tx_wave(self._records["TV_PLAY"])

    def tv_pause(self):
      self._tx_wave(self._records["TV_PAUSE"])

    def tv_vol_up(self):
      self._tx_wave(self._records["TV_VOL_UP"])

    def tv_vol_down(self):
      self._tx_wave(self._records["TV_VOL_DOWN"])

    def tv_mute(self):
      self._tx_wave(self._records["TV_MUTE"])

    def timeout(self):
      self.currently_txing = 0xFF
      self.pi.wave_tx_stop()

    def _carrier(self, gpio, frequency, micros):
       """
       Generate carrier square wave.
       """
       wf = []
       cycle = 1000.0 / frequency
       cycles = int(round(micros/cycle))
       on = int(round(cycle / 2.0))
       sofar = 0
       for c in range(cycles):
          target = int(round((c+1)*cycle))
          sofar += on
          off = target - sofar
          sofar += off
          wf.append(pigpio.pulse(1<<gpio, 0, on))
          wf.append(pigpio.pulse(0, 1<<gpio, off))
       return wf

    def _play_code(self, code = []):
      start = time.time()
      marks_wid = {}
      spaces_wid = {}

      wave = [0]*len(code)

      for i in range(0, len(code)):
          ci = code[i]
          if i & 1: # Space
              if ci not in spaces_wid:
                  self.pi.wave_add_generic([pigpio.pulse(0, 0, ci)])
                  spaces_wid[ci] = self.pi.wave_create()
              wave[i] = spaces_wid[ci]
          else: # Mark
              if ci not in marks_wid:
                  wf = self._carrier(self.GPIO, self.FREQ, ci)
                  self.pi.wave_add_generic(wf)
                  marks_wid[ci] = self.pi.wave_create()
              wave[i] = marks_wid[ci]

      delay = self.emit_time - time.time()

      if delay > 0.0:
          time.sleep(delay)

      # waveid = self.pi.wave_create()
      # self.pi.wave_send_once(waveid)
      # self.pi.wave_delete(waveid)

      self.pi.wave_chain(wave)

      while self.pi.wave_tx_busy():
          time.sleep(0.002)

      duration = time.time() - start
      print("Wave time " + format(duration))
      self.emit_time = time.time() + self.GAP_S

      for i in marks_wid:
          self.pi.wave_delete(marks_wid[i])

      marks_wid = {}

      for i in spaces_wid:
          self.pi.wave_delete(spaces_wid[i])

      spaces_wid = {}

    def _tx_wave(self, code = [], continuous = False):
      if self.continuous_tx:
        self.pi.wave_tx_stop()

      if not continuous:
        start = time.time()
      self.pi.wave_clear()
      self.waves = {}

      cycle = 1000.0 / self.FREQ
      wf = []

      for i in range(0, len(code)):
        ci = code[i]
        if i & 1:
          wf.append(pigpio.pulse(0, 0, ci))
        else:
          cycles = int(round(ci/cycle))
          on = int(round(cycle / 2.0))
          sofar = 0
          for c in range(cycles):
            target = int(round((c+1)*cycle))
            sofar += on
            off = target - sofar
            sofar += off
            wf.append(pigpio.pulse(1<<self.GPIO, 0, on))
            wf.append(pigpio.pulse(0, 1<<self.GPIO, off))
          

      self.pi.wave_add_generic(wf)
      waveid = self.pi.wave_create()
      if not continuous:
        self.pi.wave_send_once(waveid)
        while self.pi.wave_tx_busy():
          time.sleep(0.002)
        self.pi.wave_delete(waveid)

        duration = time.time() - start
        print("Wave time " + format(duration))
      else:
        self.continuous_tx = True
        self.pi.wave_send_repeat(waveid)

