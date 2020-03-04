import threading

class MyTimer:
	def __init__(self, period, callback, argument=None):
		self._period = period
		self._callback = callback
		self._argument = argument
		self._timer = threading.Timer(self._period, self._expired)
		self.running = False

	def __del__(self):
		if self.running:
			self._timer.cancel()

	def _expired(self):
		self._timer.cancel()
		if self._argument != None:
			self._callback(self._argument)
		else:
			self._callback()

	def start(self):
		if(self.running):
			self._timer.cancel()
		self._timer = threading.Timer(self._period, self._expired)
		self._timer.start()
		self.running = True

	def stop(self):
		if(self.running):
			self._timer.cancel()
		self.running = False

	def restart(self, period=None):
		if period != None:
			self._period = period
		self.start()










