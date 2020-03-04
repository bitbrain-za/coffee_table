import time
import board
import neopixel
import threading
from colour import Colour
import random
from config import Config
from my_timer import MyTimer
from enum import Enum

class Effects(Enum):
  RGB = 0
  FIRE = 1
  METEOR = 2
  CYLON = 3
  BREATHER = 4

class Indicator:

  def __init__(self, pin, length):
    self._effect = Effects.RGB
    self._thread = None
    self._thread_terminate = False
    self._thread_running = False
    self.pixels = neopixel.NeoPixel(pin, length)
    self._length = length
    self.pixels[0] = (0, 255, 0)
    self.colour = Colour(0, 0, 20)
    self.paused = False
    self._brightness = 1.0

    for i in range(1, length):
      self.pixels[i] = (0, 0, 20)

    self._backup = []
    self._temperature_pixels = []

    self.save_period = Config.TIME_TO_SAVE
    self.restore_timer = MyTimer(self.save_period, self.restore)
    self.dim_timer = MyTimer(self.save_period, self._dim)

    for i in range(0, self._length):
      self._backup.append(self.pixels[i])

    self._prepare_temperature_pixels()

    self.saved = False

  def set_mode(self, mode):
    self.stop_loop()
    print("Mode: ", format(mode.value))
    if mode == Effects.FIRE:
      self._start_fire(55, 80, 0.01)
    if mode == Effects.METEOR:
      self._start_meteor(255, 0, 255, 6, 64, 0.01)
    if mode == Effects.CYLON:
      self._start_cylon(128, 0, 0, 5, 0.01, 0)
    if mode == Effects.RGB:
      if self.colour == None:
        self.restore()

    self.pixels.auto_write = False
    self._effect = mode


  def _set_pixel(self, pixel, r, g, b):
    if pixel > self._length - 1:
      return
    if pixel < 0:
      return

    red = min(int(r), 255)
    green = min(int(g), 255)
    blue = min(int(b), 255)
    self.pixels[pixel] = (red, green, blue)

  def set_colour(self, r, g, b, transient=True, display_time=0, dim_after=0):
    if not transient:
      self.saved = False
      self.colour.rgbcolour = (int(r), int(g), int(b))

    if self._effect != Effects.RGB:
      return

    self.pixels.fill((int(r), int(g), int(b)))
    self.pixels.show()

    if dim_after != 0:
      self.set_brightness(1.0)
      self.dim_timer.restart(dim_after)

    if not transient:
      print("Saving RGB")
      self.save()
    else:
      if display_time == 0:
        self.restore_timer.restart(self.save_period)
      else:
        self.restore_timer.restart(display_time)

  def set_brightness(self, brightness, fade=False):
    if self._effect != Effects.RGB:
      self._brightness = brightness
      return
    print("New brightness: " + format(brightness))
    if not fade:
      for i in range(0, self._length):
        colour = self.pixels[i]
        new_colour = [0]*3
        for j in range(0, 3):
          new_colour[j] = colour[j] * brightness / self._brightness
        self._set_pixel(i, new_colour[0], new_colour[1], new_colour[2])
    else:
      self.colour *= 1
      colour2 = self.colour * 0.1
      self.fade(colour2, 100, 3)
    self._brightness = brightness

  def _dim(self):
    self.set_brightness(0.1)
    self.pixels.show()

  def save(self):
    for i in range(0, self._length):
      self._backup[i] = self.pixels[i]
    self.saved = True

  def restore(self):
    print("restoring")
    self.restore_timer.stop()

    if(self._effect != Effects.RGB):
      self.set_mode(self._effect)
      return

    if not self.saved:
      self.set_colour(self.colour.r, self.colour.g, self.colour.b, transient=False, dim_after=5)
    else:
      for i in range(0, self._length):
        self.pixels[i] = self._backup[i]
      self.pixels.show()
    self.saved = False

  def pause(self):
    self.paused = True
    self.save()
    self.pixels.fill((0, 0, 0))
    self.pixels.show()

  def unpause(self):
    if self._effect == Effects.RGB:
      self.restore()
    self.paused = False

  def _prepare_temperature_pixels(self):
    self.pixels.fill((0, 0, 0))

    multiplier = 255 / self._length
    for i in range(0, self._length):
      self._set_pixel(i, round(i * multiplier), 0, round(255 - (i*multiplier)))
      self._temperature_pixels.append(self.pixels[i])
      self.pixels[i] = self._backup[i]

  def set_temperature(self, temperature):
    if(self._effect != Effects.RGB):
      self.stop_loop()

    self.restore_timer.restart(self.save_period)
    self.pixels.fill((0, 0, 0))

    count = round((temperature / 100) * self._length)

    self.pixels[0:count] = self._temperature_pixels[0:count]

    self.pixels.show()

  def set_level(self, level, colour = None):
    self.pixels.fill((0, 0, 0))
    if colour == None:
      colour = self.colour

    count = round((level / 100) * self._length)
    for i in range(0, count):
      self._set_pixel(i, colour.r, colour.g, colour.b)
    self.pixels.show()

  def shoot(self):
    for i in range(0, self._length):
      self.pixels[i] = (0, 20, 0)
      time.sleep(0.100)
    for i in range(0, self._length):
      self.pixels[i] = (0, 0, 10)
      time.sleep(0.100)
    for i in range(0, self._length):
      self.pixels[i] = (0, 0, 0)
      time.sleep(0.100)
  
  def fade_from_to(self, colour1, colour2, steps, interval):
    while (self._thread_running): pass
    self._thread = threading.Thread(target=self._fade, args=(colour1, colour2, steps, interval))
    self._thread.daemon = True
    self._thread.start()

  def fade(self, colour2, steps, interval):
    self.fade_from_to(self.colour, colour2, steps, interval)

  def _fade(self, colour1, colour2, steps, interval):
    self._thread_running = True
    lastUpdate = time.time() - interval
    interval = interval / steps

    for i in range(1, steps + 1):
      r = round(((colour1.r * (steps - i)) + (colour2.r * i)) / steps)
      g = round(((colour1.g * (steps - i)) + (colour2.g * i)) / steps)
      b = round(((colour1.b * (steps - i)) + (colour2.b * i)) / steps)
      
      while ((time.time() - lastUpdate) < interval):
        pass

      colour = Colour(r, g, b)
      for j in range(0, self._length):
        if not self.paused:
          self._set_pixel(j, colour.r, colour.g, colour.b)

      lastUpdate = time.time()
    self._thread_running = False
    self.colour = colour2

  def blink(self, r, g, b):
    self.set_colour(r, g, b, transient=True, display_time=0.5)

### Effects ###
  # Ported from: https://www.tweaking4all.com/hardware/arduino/adruino-led-strip-effects/

  ### Base ###

  def stop_loop(self):
    self._thread_terminate = True
    while self._thread_running:
      pass

  ### Cylon ###

  def _start_cylon(self, r, g, b, EyeSize, SpeedDelay, ReturnDelay):
    while (self._thread_running): pass
    self._thread = threading.Thread(target=self._cylon, args=(r, g, b, EyeSize, SpeedDelay, ReturnDelay))
    self._thread.daemon = True
    self._thread.start()

  def _cylon(self, red, green, blue, EyeSize, SpeedDelay, ReturnDelay):
    self._thread_terminate = False
    self._thread_running = True
    while not self._thread_terminate:
      if not self.paused:
        for i in range(0-EyeSize, self._length + EyeSize):
          if self._thread_terminate:
            self._thread_running = False
            return

          self.pixels.fill((0, 0, 0))
          self._set_pixel(i, round(red/10), round(green/10), round(blue/10))
          for j in range(1, EyeSize):
            self._set_pixel(i + j, red, green, blue)
          self._set_pixel(i + EyeSize, round(red/10), round(green/10), round(blue/10))
          if not self.paused:
            self.pixels.show()
          time.sleep(SpeedDelay)

        time.sleep(ReturnDelay)

        for i in range(self._length + EyeSize, 0-EyeSize, -1):
          if self._thread_terminate:
            self._thread_running = False
            return

          self.pixels.fill((0, 0, 0))
          self._set_pixel(i, round(red/10), round(green/10), round(blue/10))
          for j in range(EyeSize, 0, -1):
            self._set_pixel(i-j, red, green, blue)
          self._set_pixel(i - EyeSize, round(red/10), round(green/10), round(blue/10))
          if not self.paused:
            self.pixels.show()
          time.sleep(SpeedDelay)

      time.sleep(ReturnDelay)
    self._thread_running = False

  ### Fire ###

  def _start_fire(self, cooling, sparking, speed_delay):
    self._thread_terminate = False
    while (self._thread_running): pass
    self._thread = threading.Thread(target=self._fire, args=(cooling, sparking, speed_delay))
    self._thread.daemon = True
    print("Starting a fire")
    self._thread.start()

  def _fire(self, cooling, sparking, speed_delay):
    heat = [0]*self._length
    cooldown = 0
    self._thread_running = True
    
    while not self._thread_terminate:
      if not self.paused:
        for i in range(0, self._length):
          cooldown = random.randint(0, round(((cooling * 10) / self._length) + 20))
          if cooldown > heat[i]:
            heat[i] = 0
          else:
            heat[i] = heat[i] - cooldown

        for i in range(self._length - 1, 3, -1):
          heat[i] = (heat[i - 1] + heat[i - 2] + heat[i - 2]) / 3

        if random.randint(0, 255) < sparking:
          y = random.randint(0, 7)
          heat[y] = heat[y] + random.randint(160, 255)

        for i in range(0, self._length):
          self._set_pixel_heat_colour(i, heat[i])

        if not self.paused:
          self.pixels.show()
        time.sleep(speed_delay)

    self._thread_running = False

  def _set_pixel_heat_colour(self, pixel, temperature):

    t192 = round((temperature/255.0)*191)

    heatramp = t192 & 0x3F
    heatramp <<= 2
   
    if( t192 > 0x80):
      self._set_pixel(pixel, 255, 255, heatramp)
    elif( t192 > 0x40 ):
      self._set_pixel(pixel, 255, heatramp, 0)
    else:
      self._set_pixel(pixel, heatramp, 0, 0)

  ### Meteor ###
  def _start_meteor(self, red, green, blue, size, trail_decay, speed):
    self._thread_terminate = False
    while (self._thread_running): pass
    self._thread = threading.Thread(target=self._meteor, args=(red, green, blue, size, trail_decay, speed))
    self._thread.daemon = True
    print("Pew pew")
    self._thread.start()

  def _meteor(self, red, green, blue, size, trail_decay, speed):
    self.pixels.fill((0, 0, 0))
    self._thread_running = True

    while not self._thread_terminate:
      if not self.paused:
        for i in range(0, self._length * 2):
          # fade
          for j in range(0, self._length):
            if (random.randint(0, 10) < 5):
              self.fade_to_black(j, trail_decay)

          for j in range(0, size):
            if (( i - j ) < self._length):
              self._set_pixel(i - j, red, green, blue)

          if not self.paused:
            self.pixels.show()

          if self._thread_terminate:
            self._thread_running = False
            return

          time.sleep(speed)
    self._thread_running = False

  def fade_to_black(self, pixel, fade_value):
    old_colour = self.pixels[pixel]
    r = old_colour[0]
    g = old_colour[1]
    b = old_colour[2]

    if r <= 10:
      r = 0
    else:
      r = r - (r * fade_value / 256)
    if g <= 10:
      g = 0
    else:
      g = g - (g * fade_value / 256)
    if b <= 10:
      b = 0
    else:
      b = b - (b * fade_value / 256)

    self._set_pixel(pixel, r, g, b)