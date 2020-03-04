import threading
import serial

class Comms:
	def __init__(self):
		self.ser = serial.Serial(            
		  port='/dev/serial0',
		  baudrate = 9600,
		  parity=serial.PARITY_NONE,
		  stopbits=serial.STOPBITS_ONE,
		  bytesize=serial.EIGHTBITS,
		  timeout=1
		)
		self.mutex = threading.RLock()

	def send_text(self, text):
		with self.mutex:
			self.ser.write(bytes(text, 'utf-8'))
			print("Sending: " + text)

	def send_packet(self, payload):
		text = "S" + payload + ","
		self.send_text(text)

	def send_data(self, data):
		string = ",".join(str(x) for x in data)
		self.send_packet(string)

	def send(self, command, message):
		string = hex(command)[2:]
		if(message != None):
			string += "," + message
		self.send_packet(string)