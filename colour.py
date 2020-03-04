class Colour:
  def __init__(self, r, g, b):
    self.r = r
    self.g = g
    self.b = b
    self._brightness = 1.0

  def __getattr__(self, attr):
    if attr == "rgbcolour":
      return (self.r, self.g, self.b)
    else:
      raise AttributeError

  def __setattr__(self, attr, val):
    if attr == "rgbcolour":
      self.r = val[0]
      self.g = val[1]
      self.b = val[2]
    else:
      super().__setattr__(attr, val)

  def __mul__(self, b):
    c = Colour(self.r*b, self.g*b, self.b*b)
    c._brightness = b
    return c

  def __imul__(self, b):
    b /= self._brightness
    self.r *= b
    self.g *= b
    self.b *= b
    self._brightness = b
    return self

  def __add__(self, b):
    return Colour(self.r + b.r, self.g + b.g, self.b +b.b)

  def set_brightness(self, brightness):
    if self._brightness < 1:
      for i in range(0, 3):
        self.rgbcolour[i] /= self._brightness
    self._brightness = brightness
    for i in range(0, 3):
      self.rgbcolour[i] *= self._brightness

  def __dir__(self):
    return ("rgbcolour")