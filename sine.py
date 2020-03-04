import math

class Sine:
  def __init__(self):
    self.wave = [0]*360

    x = math.pi
    for i in range(0, 240):
      # print (format(math.cos(x)))
      self.wave[i] = round((math.cos(x) + 1) * 255 / 2)
      x += math.pi/120

    # self.bubbleSort()

    # string = ""
    # for i in range(0, 360):
    #   if (i % 8) == 0:
    #     print(string)
    #     string = ""
    #   string += format(self.wave[i]) + ","

  def bubbleSort(self): 
    n = len(self.wave) 
  
    for i in range(n): 
      for j in range(0, n-i-1): 
        if self.wave[j] > self.wave[j+1] : 
          self.wave[j], self.wave[j+1] = self.wave[j+1], self.wave[j] 


  def get_triangle(self, angle):
    r = self.wave[(angle+120)%360]
    g = self.wave[angle]
    b = self.wave[(angle+240)%360]
    return (r, g, b)
