from gpiozero import Button, LED
from signal import pause
import json
import pigpio
import time

class GPIO:
  def __init__(self, logger):
    self._thread = None
    self._thread_terminate = False
    self.running = False
    self._on_button = None

    self._logger = logger

    self._in_callback_mutex = threading.Lock()
    self._callback_mutex = threading.RLock()

    self._logger.debug("Starting GPIO service")
    self.send_button("Service Started")

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

    self.ir = LED(14)

    self.button1 = Button(26, pull_up = True)
    self.button1.hold_time = 2
    # button1.when_pressed = lambda: send_message(button1, message = "pressed")
    self.button1.when_pressed = ir.toggle
    self.button1.when_released = lambda: send_message(button1, message = "released")
    self.button1.when_held = lambda: send_message(button1, message = "held")

    self.pin_a = Button(13, pull_up = True)
    self.pin_b = Button(19, pull_up = True)

    pin_a.when_pressed = pin_a_rising
    pin_b.when_pressed = pin_b_rising

    last_tick = 0
    in_code = False
    code = []
    fetching_code = False


  def send_message(button, message = ""):
      print(str(button.pin.number) + " " + message)
      play_code(records["OFF"])


  def pin_a_rising():
      if pin_b.is_pressed: send_message(pin_a, "-1")

  def pin_b_rising():
      if pin_a.is_pressed: send_message(pin_a, "1")



def carrier(gpio, frequency, micros):
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

def play_code(code):
   marks_wid = {}
   spaces_wid = {}

   wave = [0]*len(code)

   for i in range(0, len(code)):
      ci = code[i]
      if i & 1: # Space
         if ci not in spaces_wid:
            pi.wave_add_generic([pigpio.pulse(0, 0, ci)])
            spaces_wid[ci] = pi.wave_create()
         wave[i] = spaces_wid[ci]
      else: # Mark
         if ci not in marks_wid:
            wf = carrier(GPIO, FREQ, ci)
            pi.wave_add_generic(wf)
            marks_wid[ci] = pi.wave_create()
         wave[i] = marks_wid[ci]

   pi.wave_chain(wave)

   while pi.wave_tx_busy():
      time.sleep(0.002)


   for i in marks_wid:
      pi.wave_delete(marks_wid[i])

   marks_wid = {}

   for i in spaces_wid:
      pi.wave_delete(spaces_wid[i])

   spaces_wid = {}


pi = pigpio.pi() # Connect to Pi.

if not pi.connected:
   exit(0)

try:
   f = open(FILE, "r")
except:
   print("Can't open: {}".format(FILE))
   exit(0)

records = json.load(f)

f.close()

pi.set_mode(GPIO, pigpio.OUTPUT) # IR TX connected to this GPIO.

pi.wave_add_new()

pause()

pi.stop() # Disconnect from Pi.





