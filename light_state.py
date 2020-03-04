class LightState:
	def __init__(self, name, initial):
		self.name = name
		self.brightness = initial

	def increase_brightness(self):
		if self.brightness < 255:
			self.brightness += 1
		return self.brightness

	def lower_brightness(self):
		if self.brightness > 0:
			self.brightness -= 1
		return self.brightness


