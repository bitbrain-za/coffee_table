import board

class HAL:

#
#   REC1    BTN1    BTN2    BTN3    REC2    BTN4    BTN5    BTN6    REC3
#   Lights  PC      TV      Pause   Volume  Scene1  Scene2  Scene3  Aircon

# REC1 - Lounge Lights:
#   Up - Increase Brightness/cycle rgb
#   Down - Reduce Brightness/cycle rgb
#   Hold - Change mode:
#     * If held, go into rgb mode.
#     * Start a timer to revert to normal
#     * Volume -> RGB
#   Press - Lights on/off

# BTN1
#   * Press - turn on PC 
#   * hold - turn off PC
# - Do it this way to stop accidentally toggling PC power

  LIGHTS_A = 24
  LIGHTS_B = 25
  LIGHTS_C = 23

  VOL_A = 5
  VOL_B = 12
  VOL_C = 6

  AC_A = 19
  AC_B = 13
  AC_C = 16

  BTN1 = 20
  BTN2 = 26
  BTN3 = 21

  BTN4 = 17
  BTN5 = 27
  BTN6 = 22

  DOS = 15
  LOCK = 4

  IR_TX = 14
  WS2812B_DATA = board.D18
