#!/usr/bin/env python3

from mqtt import MQTT
from rfid import RFID
from arduino_remote import Remote, Key
from uart import Comms
from hal import HAL
from config import Config
from rotary_encoder import RotaryEncoder
from gpiozero import RGBLED, Button, OutputDevice
from indicator import Indicator, Effects
from colour import Colour
import board
import threading
import time
import secrets
import logging
from logging.handlers import RotatingFileHandler
from signal import pause
from sine import Sine
import eiscp


class Coordinator:

########## Constructor ##########

  def __init__(self):
    self.ac_on = False

    self._init_logger()
    self._init_neopixel()
    self._init_ir()

    self._init_mqtt()
    self._init_lock()
    self._init_rfid()
    self._initialise_volume_control()
    self._initialise_ac()
    self._initialise_brightness_control()
    self._init_buttons()

    self._mqtt_client.send_message("boot", "started")
    self.strip.set_mode(Effects.RGB)

########## Logger ##########

  def _init_logger(self):
    self.formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    self.handler = RotatingFileHandler(filename='/home/pi/app/coffee_table.log', mode='a', maxBytes=20*1024*1024, backupCount=2, encoding=None, delay=0)
    self.handler.setFormatter(self.formatter)
    self.logger = logging.getLogger("coffee_table")
    self.logger.setLevel(logging.WARN)
    self.logger.addHandler(self.handler)
    self.logger.debug("Starting coordinator Service")

########## Lock ##########

  def _init_lock(self):
    self.lock = OutputDevice(HAL.LOCK)
    self.lock.off()

  def open_lock(self, time_s):
    self.strip.pause()
    self.lock.on()
    threading.Timer(time_s, self.close_lock).start()

  def close_lock(self):
    self.lock.off()
    self.strip.unpause()

########## RFID Reader ##########

  def _init_rfid(self):
    self._reader = RFID(self.logger)
    self._reader.on_tag =  lambda sender, tag: self._mqtt_client.send_message("tags", tag)
    self._reader.start()

########## IR ##########
  def _init_ir(self):
    self.comms = Comms()
    self.device_state_tv = False
    self.device_state_amp = False
    self.remote = Remote(1, Config.REMOTE_AMP, self.logger, self.comms)

  def turn_on_devices(self):
    if not self.device_state_tv:
      self.remote.press_button(Key.TV_POWER, 1)
      self.device_state_tv = not self.device_state_tv
    if not self.device_state_amp:
      self.remote.press_button(Key.AMP_POWER, 1)
      self.device_state_amp = not self.device_state_amp

########## Room Lights ##########

  def _initialise_brightness_control(self):
    self.lights_held = False
    self.sine = Sine()
    self.rgb_mode_timer = threading.Timer(Config.RGB_MODE_TIMER, self.leave_rgb_mode)
    self.lights_tx_timer = threading.Timer(Config.LIGHTS_DELAY_TO_SEND, self.lights_send_brightness)
    self.lights_are_on = True
    self.brightness = 0xFF
    self.rgb_long = 0x00FFFFFF
    self.brightness_control = RotaryEncoder(HAL.LIGHTS_A, HAL.LIGHTS_B, maximum=255, minimum=0, initial=255, step_size=5)
    self.brightness_control.on_clockwise = self.brightness_up
    self.brightness_control.on_counter_clockwise = self.brightness_down
    self._mqtt_client.on_rgb = self.on_rgb_message

    self.btn_lights = Button(HAL.LIGHTS_C, pull_up = True)
    self.btn_lights.hold_time = Config.BTN_HOLD_TIME
    self.btn_lights.when_held      = self.enter_rgb_mode
    self.btn_lights.when_released  = self.toggle_lights
    self.rgb_angle = 0

  def brightness_up(self):
    self.strip.set_temperature(self.brightness_control.percent())
    self.lights_tx_timer.cancel()
    self.lights_tx_timer = threading.Timer(Config.LIGHTS_DELAY_TO_SEND, self.lights_send_brightness)
    self.lights_tx_timer.start()

  def brightness_down(self):
    self.strip.set_temperature(self.brightness_control.percent())
    self.lights_tx_timer.cancel()
    self.lights_tx_timer = threading.Timer(Config.LIGHTS_DELAY_TO_SEND, self.lights_send_brightness)
    self.lights_tx_timer.start()

  def rgb_angle_changed(self):
    self.rgb_angle = self.brightness_control.value
    self.colour_picker = self.sine.get_triangle(self.rgb_angle * Config.DEGREES_PER_CLICK)
    self.strip.pixels.fill(self.colour_picker)
    self.strip.pixels.show()

    self.lights_tx_timer.cancel()
    self.lights_tx_timer = threading.Timer(Config.LIGHTS_DELAY_TO_SEND, self.lights_send_rgb)
    self.lights_tx_timer.start()

    self.rgb_mode_timer.cancel()
    self.rgb_mode_timer = threading.Timer(Config.RGB_MODE_TIMER, self.leave_rgb_mode)
    self.rgb_mode_timer.start()

  def lights_send_brightness(self):
    print("Updating Brightness")
    self._mqtt_client.send_message("lights/brightness", format(self.brightness_control.value))

  def lights_send_rgb(self):
    string = ",".join(str(x) for x in self.colour_picker)
    print("Updating RGB")
    self._mqtt_client.send_message("lights/rgb", string)

  def enter_rgb_mode(self):
    self.lights_held = True
    self.strip.set_mode(Effects.RGB)
    self.strip.blink(0, 0, 255)
    self.rgb_mode_timer.cancel()
    print("RGB Mode")
    self.strip.set_brightness(1)
    self.brightness_control.loop = True
    self.brightness_control.maximum = round(360 / Config.DEGREES_PER_CLICK) - 1
    self.brightness_control.step = 1
    self.brightness_control.value = self.rgb_angle
    self.brightness_control.on_clockwise = None 
    self.brightness_control.on_counter_clockwise = None
    self.brightness_control.on_value_change = self.rgb_angle_changed
    self.rgb_mode_timer.cancel()
    self.rgb_mode_timer = threading.Timer(Config.RGB_MODE_TIMER, self.leave_rgb_mode)
    self.rgb_mode_timer.start()

  def leave_rgb_mode(self):
    self.rgb_mode_timer.cancel()
    print("Normal Mode")
    self.brightness_control.loop = False
    self.brightness_control.maximum = 255
    self.brightness_control.step = 5
    self.brightness_control.value = 255
    self.brightness_control.on_clockwise = self.brightness_up
    self.brightness_control.on_counter_clockwise = self.brightness_down
    self.brightness_control.on_value_change = None
    self.rgb_mode_timer.cancel()
    self.strip.restore()

  def toggle_lights(self):
    if(self.lights_held):
      self.lights_held = False
      return
    self._mqtt_client.send_message("lights/brightness", "toggle")

  def on_rgb_message(self, r, g, b):
    self.strip.set_colour(r, g, b, transient=False, dim_after=5)
    
########## Neopixel ##########

  def _init_neopixel(self):
    self.strip = Indicator(HAL.WS2812B_DATA, 55)
    self.strip.set_mode(Effects.CYLON)
    self.effect = 1

  def cycle_effect(self):
    
    if self.effect == 0:
      self.strip.set_mode(Effects.RGB)

    if self.effect == 1:
      self.strip.set_mode(Effects.FIRE)

    if self.effect == 2:
      self.strip.set_mode(Effects.METEOR)

    if self.effect == 3:
      self.strip.set_mode(Effects.CYLON)

    if self.effect == 4:
      self.strip.set_mode(Effects.RGB)
      self.strip.set_colour(40, 0, 0, False)

    if self.effect == 5:
      self.strip.set_mode(Effects.RGB)
      self.strip.set_colour(0, 40, 0, False)

    if self.effect == 6:
      self.strip.set_mode(Effects.RGB)
      self.strip.set_colour(0, 0, 40, False)
      self.effect = -1

    self.effect += 1

########## Volume ##########

  def _initialise_volume_control(self):
    self.receiver = eiscp.eISCP('192.168.1.31')
    self.source = 1
    self.tv_mode = False
    self.volume_power_held = False

    self.button_amp_power = Button(HAL.VOL_C, pull_up = True)
    self.button_amp_power.hold_time = Config.BTN_HOLD_TIME
    self.button_amp_power.when_held      = self.btn_volume_held
    self.button_amp_power.when_released  = self.btn_volume_release

    self.volume_control = RotaryEncoder(HAL.VOL_A, HAL.VOL_B, maximum=60, minimum=0, initial=30, step_size=1)
    self.volume_control.on_clockwise = self.volume_up
    self.volume_control.on_counter_clockwise = self.volume_down
    self.btnvol_was_held = False

  def btn_volume_held(self):
    self.btnvol_was_held = True
    self.strip.blink(0, 0, 255)

  def btn_volume_release(self):
    if not self.btnvol_was_held:
      self._mqtt_client.send_message("amp", "short")
    else:
      self._mqtt_client.send_message("amp", "long")
    self.btnvol_was_held = False

  def switch_mode(self):
    self.tv_mode = not self.tv_mode

  def volume_up(self):
    self.strip.set_temperature(self.volume_control.percent())
    self.receiver.raw('MVLUP')

  def volume_down(self):
    self.strip.set_temperature(self.volume_control.percent())
    self.receiver.raw('MVLDOWN')

########## Aircon ##########

  def _initialise_ac(self):
    self.ac_power = Button(HAL.AC_C, pull_up = True)
    self.ac_control = RotaryEncoder(HAL.AC_A, HAL.AC_B, maximum=30, minimum=16, initial=24, step_size=1, can_zero = False)
    self.ac_control.on_value_change = self.set_ac
    self.ac_power.when_released  = self.toggle_ac
    self.ac_timer = threading.Timer(Config.AIRCON_DELAY_TO_SEND, self.send_ac_temp)
    self._mqtt_client.on_ac_temp = self.update_temp

  def update_temp(self, temp):
    self.ac_control.value = int(temp)
    self.strip.set_temperature(self.ac_control.percent())

  def set_ac(self):
    self.strip.set_temperature(self.ac_control.percent())
    self.ac_timer.cancel()
    self.ac_timer = threading.Timer(Config.AIRCON_DELAY_TO_SEND, self.send_ac_temp)
    self.ac_timer.start()

  def send_ac_temp(self):
    self._mqtt_client.send_message("ac/set_temp", format(self.ac_control.value))

  def toggle_ac(self):
    self._mqtt_client.send_message("btnAC", "click")

########## Buttons ##########
  def _init_buttons(self):
    self.btn1 = Button(HAL.BTN1, pull_up = True)
    self.btn1.when_held     = self.btn1_held
    self.btn1.when_released = self.btn1_release
    self.btn1_was_held = False
    self.btn2 = Button(HAL.BTN2, pull_up = True)
    self.btn2.when_held     = self.btn2_held
    self.btn2.when_released = self.btn2_release
    self.btn2_was_held = False
    self.btn3 = Button(HAL.BTN3, pull_up = True)
    self.btn3.when_held     = self.btn3_held
    self.btn3.when_released = self.btn3_release
    self.btn3_was_held = False
    self.btn4 = Button(HAL.BTN4, pull_up = True)
    self.btn4.when_held     = self.btn4_held
    self.btn4.when_released = self.btn4_release
    self.btn4_was_held = False
    self.btn5 = Button(HAL.BTN5, pull_up = True)
    self.btn5.when_held     = self.btn5_held
    self.btn5.when_released = self.btn5_release
    self.btn5_was_held = False
    self.btn6 = Button(HAL.BTN6, pull_up = True)
    self.btn6.when_held     = self.btn6_held
    self.btn6.when_released = self.btn6_release
    self.btn6_was_held = False

  # LED Fun
  def btn1_held(self):
    self.btn1_was_held = True
    self._mqtt_client.send_message("btn1", "hold")
    self.strip.blink(0, 0, 255)
  def btn1_release(self):
    if not self.btn1_was_held:
      self._mqtt_client.send_message("btn1", "click")
      self.cycle_effect()
    self.btn1_was_held = False

  # Button 2
  def btn2_held(self):
    self.btn2_was_held = True
    self._mqtt_client.send_message("btn2", "hold")
    self.strip.blink(0, 0, 255)
  def btn2_release(self):
    if not self.btn2_was_held:
      self._mqtt_client.send_message("btn2", "click")
      print("Btn2 released")  
    self.btn2_was_held = False

  def btn3_held(self):
    self.btn3_was_held = True
    self._mqtt_client.send_message("btn3", "hold")
    self.strip.blink(0, 0, 255)
  def btn3_release(self):
    if not self.btn3_was_held:
      self._mqtt_client.send_message("btn3", "click")
      print("Btn3 released")
    self.btn3_was_held = False

  def btn4_held(self):
    self.btn4_was_held = True
    self._mqtt_client.send_message("btn4", "hold")
    self.strip.blink(0, 0, 255)
  def btn4_release(self):
    if not self.btn4_was_held:
      self._mqtt_client.send_message("btn4", "click")
      print("Btn4 released")  
    self.btn4_was_held = False

  #Play/Pause TV
  def btn5_held(self):
    self.btn5_was_held = True
    self._mqtt_client.send_message("btn5", "hold")
    self.strip.blink(0, 0, 255)
  def btn5_release(self):
    if not self.btn5_was_held:
      self._mqtt_client.send_message("btn5", "click")
      print("Btn5 released")  
    self.btn5_was_held = False

  # PC On/Off
  def btn6_held(self):
    self.btn6_was_held = True
    self._mqtt_client.send_message("btn6", "hold")
    self.strip.blink(0, 0, 255)
  def btn6_release(self):
    if not self.btn6_was_held:
      self._mqtt_client.send_message("btn6", "click")
      print("Btn6 released")  
    self.btn6_was_held = False

########## Command Handler ##########

  def handle_command(self, command):
    if command == "unlock":
      self.open_lock(Config.OPEN_LOCK_TIME)
    elif command == "lock":
      self.lock.off()
    elif command == "fire":
      self.strip.set_mode(Effects.FIRE)
    elif command == "cylon":
      self.strip.set_mode(Effects.CYLON)
    elif command == "stop_rgb":
      self.strip.set_mode(Effects.RGB)
      self.strip.set_colour(0, 10, 0, False)
    elif command == "devices_on":
      self.turn_on_devices()
    elif command == "source_cd":
      self.remote.press_button(Key.AMP_CD, 1)
      self.source = 2
    elif command == "source_video1":
      self.remote.press_button(Key.AMP_VIDEO1, 1)
      self.source = 3
    elif command == "source_video2":
      self.remote.press_button(Key.AMP_VIDEO2, 1)
      self.source = 4
    elif command == "source_aux":
      self.remote.press_button(Key.AMP_AUX, 1)
      self.source = 1
    elif command == "amp_power":
      self.remote.press_button(Key.AMP_POWER, 1)
    elif command == "tv_power":
      self.remote.press_button(Key.TV_POWER, 1)
    elif command == "pause":
      self.remote.press_button(Key.TV_PAUSE, 1)
    elif command == "play":
      self.remote.press_button(Key.TV_PLAY, 1)
    else:
      self.logger.debug("unrecognized command: " + command)

########## MQTT ##########

  def _init_mqtt(self):
    self._mqtt_client = MQTT(secrets.mqtt_broker, secrets.mqtt_port, secrets.mqtt_user, secrets.mqtt_pass, self.logger)
    self._mqtt_client.start()

    while self._mqtt_client.connected != True:
        time.sleep(0.1)

    self._mqtt_client.send_message("buttons", "Running")
    self._mqtt_client.send_message("lights/lounge", "update")
    self._mqtt_client.on_command = self.handle_command

########## Main ##########

  def run(self):
    try:
      pause()

    except KeyboardInterrupt:
      self._reader.stop()
      self._mqtt_client.stop()

      self.logger.info("App closing")

coordinator = Coordinator()
coordinator.run()
