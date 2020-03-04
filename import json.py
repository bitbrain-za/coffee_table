import json

x = {
	"One": {"mark": 563, "space":1688},
	"Zero": {"mark": 563, "space":563},
	"Header": {"mark": 9000, "space":4500},
	"Repeat": {"mark": 9000, "space":2250},
	"pulse_trail": 563,
	"Gap": 108000,

	"pre_data_bytes": 1,
	"pre_data" : "1D",

	"code_length": 3,

	"Keys":
	[
		{"name":"KEY_POWER", 	"id":0,  "code": "00B946"},
		{"name":"KEY_VOL_UP", 	"id":1,  "code": "00D926"},
		{"name":"KEY_MUTE", 	"id":2,  "code": "0039C6"},
		{"name":"KEY_VOL_DOWN", "id":3,  "code": "0059A6"},
		{"name":"KEY_DVD", 		"id":4,  "code": "C001FE"},
		{"name":"KEY_AUX", 		"id":5,  "code": "00C936"},
		{"name":"KEY_CD", 		"id":6,  "code": "0049B6"},
		{"name":"KEY_TAPE", 	"id":7,  "code": "00A956"},
		{"name":"KEY_TUNER", 	"id":8,  "code": "008976"},
		{"name":"KEY_VIDEO1", 	"id":9,  "code": "0040BF"},
		{"name":"KEY_VIDEO2", 	"id":10, "code": "006996"},
		{"name":"KEY_BASS", 	"id":11, "code": "40EA15"}
	]
}
# convert into JSON:
y= json.dumps(x)

_data = json.loads(y)
# the result is a JSON string:
print(_data)

one = [0]*2
zero = [0]*2
header = [0]*2
repeat = [0]*2

one[0] = _data["One"]["mark"]
one[1] = _data["One"]["space"]
zero[0] = _data["Zero"]["mark"]
zero[1] = _data["Zero"]["space"]
header[0] = _data["Header"]["mark"]
header[1] = _data["Header"]["space"]
pulse_trail = _data["pulse_trail"]

gap = _data["Gap"]
predata = int(_data["pre_data"], 16)
print(hex(predata))
pre_data_bytes = _data["pre_data_bytes"]

code_length = _data["code_length"]
codes = _data["Keys"]
try:
	repeat[0] = _data["Repeat"]["mark"]
	repeat[1] = _data["Repeat"]["space"]
	repeat_length = len(repeat)
except KeyError:
	repeat_length = 0

print("Remote - Loaded remote with " + format(len(codes)) + " codes")

for c in codes:
    print("Key: "+c["name"])
    print("ID: "+hex(c["id"]))
    print("Code: "+c["code"])
 #   for i in c:
 #       print(i)
 #       print((c[i])[0])
 
data = (pre_data_bytes,
		code_length,
		len(codes),
		header[0],
		header[1],
		one[0],
		one[1],
		zero[0],
		zero[1],
		pulse_trail,
		gap,
		repeat_length,
		repeat[0],
		repeat[1])
string = ",".join(hex(x)[2:] for x in data)
print(string)
  