from gpiozero import Button, LED
import threading

class RotaryEncoder:
  def __init__(self, pinA, pinB, minimum = 0x00, maximum = 0xFF, initial = 0x00, step_size = 1, can_zero = True, loop = False):
    self.pin_a = Button(pinA, pull_up = True)
    self.pin_b = Button(pinB, pull_up = True)
    self.min = minimum
    self.max = maximum
    self.value = initial
    self.step = step_size
    self._in_callback_mutex = threading.Lock()
    self._callback_mutex = threading.RLock()
    self.can_zero = can_zero
    self.loop = loop

    self.on_clockwise = None
    self.on_counter_clockwise = None
    self.on_value_change = None

    self.pin_a.when_pressed = self.pin_a_rising
    self.pin_b.when_pressed = self.pin_b_rising

  def pin_a_rising(self):
    if self.pin_b.is_pressed: 
      if not self.loop:
        if self.value > self.min:
          self.value -= self.step
          if self.value < self.min:
            self.value = self.min
        if not self.can_zero:
          if self.value == self.min:
            self.value = self.min + self.step
      else:
        self.value += self.max
        self.value -= self.step
        self.value = self.value % self.max
      self._on_counter_clockwise_callback()
      self._on_value_change_callback()

  def pin_b_rising(self):
    if self.pin_a.is_pressed: 
      if not self.loop:
        if self.value < self.max:
          self.value += self.step
          if self.value > self.max:
            self.value = self.max
      else:
        self.value += self.step
        self.value = self.value % self.max
      self._on_clockwise_callback()
      self._on_value_change_callback()

  def _on_clockwise_callback(self):
    with self._callback_mutex:
      if self.on_clockwise:
        with self._in_callback_mutex:
          self.on_clockwise()

  def _on_counter_clockwise_callback(self):
    with self._callback_mutex:
      if self.on_counter_clockwise:
        with self._in_callback_mutex:
          self.on_counter_clockwise()

  def _on_value_change_callback(self):
    with self._callback_mutex:
      if self.on_value_change:
        with self._in_callback_mutex:
          self.on_value_change()

  def percent(self):
    span = self.max - self.min
    norm = self.value - self.min
    return ((norm/span) * 100)

  @property
  def on_clockwise(self):
    return self._on_clockwise

  @on_clockwise.setter
  def on_clockwise(self, func):
    with self._callback_mutex:
      self._on_clockwise = func

  @property
  def on_counter_clockwise(self):
    return self._on_counter_clockwise

  @on_counter_clockwise.setter
  def on_counter_clockwise(self, func):
    with self._callback_mutex:
      self._on_counter_clockwise = func

  @property
  def on_value_change(self):
    return self._on_value_change

  @on_value_change.setter
  def on_value_change(self, func):
    with self._callback_mutex:
      self._on_value_change = func