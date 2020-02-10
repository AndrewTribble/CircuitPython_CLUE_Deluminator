
import time
import board
import pulseio
import terminalio
from adafruit_clue import clue
from adafruit_display_text import label
import displayio
from adafruit_display_shapes.rect import Rect

clue._white_leds.deinit()

led = pulseio.PWMOut(board.WHITE_LEDS, frequency=5000, duty_cycle=0)
# previous iteration button value
old_a_val = clue.button_a
# previous iteration button value
old_b_val = clue.button_b

DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240

STATE_IDLE = 0;
STATE_CHARGING = 1;
STATE_DISCHARGING = 2;
CUR_STATE = STATE_IDLE

MAX_CHARGE_LEVEL = 60 * 1000  # 60 seconds in ms
MAX_CHARGE_BRIGHTNESS = 65535  # full pwm duty_cycle

CHARGING_MAGIC_MODIFIER = 12

TICK_INTERVAL = 100  # ms

charge_level = 0
charge_brightness = 0

last_tick_time = 0

cur_clear_brightness = 0


""" 
Called every TICK_INTERVAL while discharging.
Decrements the charge_level and charge_brightness.
"""


def discharge_tick():
    global charge_level, charge_brightness
    charge_level -= 250
    charge_level = max(0, charge_level)
    if charge_level < MAX_CHARGE_LEVEL // 2:
        charge_brightness = int(charge_brightness * 0.985)


""" 
Called every TICK_INTERVAL while charging.
increments the charge_level and sets charge brightness to 
average between current brightness and level from sensor.
"""


def charge_tick():
    global charge_level, charge_brightness
    charge_level += 100 * CHARGING_MAGIC_MODIFIER
    charge_level = min(MAX_CHARGE_LEVEL, charge_level)
    if cur_clear_brightness > charge_brightness:
        charge_brightness = int((charge_brightness + cur_clear_brightness) / 2)


# Make the display context
splash = displayio.Group(max_size=10)
board.DISPLAY.show(splash)
# Make a background color fill
color_bitmap = displayio.Bitmap(320, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x0
bg_sprite = displayio.TileGrid(color_bitmap, x=0, y=0, pixel_shader=color_palette)
splash.append(bg_sprite)

# set progress bar width and height relative to board's display
x = board.DISPLAY.width - 10
y = board.DISPLAY.height // 3

rect = Rect(-240, 5, 240, y, fill=0x00FF00)

# Append progress_bar to the splash group
splash.append(rect)

text_brightness = label.Label(terminalio.FONT, text="Brightness: 100 %")
text_brightness.anchor_point = (0.5, 1.0)
text_brightness.anchored_position = (DISPLAY_WIDTH / 4, DISPLAY_HEIGHT / 2)

text_group = displayio.Group(max_size=1, scale=2, x=0, y=0)

text_group.append(text_brightness)
splash.append(text_group)
while True:
    cur_time = int(time.monotonic() * 1000)
    cur_clear_brightness = clue.color[3]
    # set current button state to variable
    cur_a_val = clue.button_a
    cur_b_val = clue.button_b
    if CUR_STATE != STATE_DISCHARGING:
        if cur_a_val:  # if the button is down
            CUR_STATE = STATE_CHARGING
        else:
            CUR_STATE = STATE_IDLE

    if cur_b_val and not old_b_val:  # if the button was released
        print("b released")
        if CUR_STATE != STATE_DISCHARGING:
            CUR_STATE = STATE_DISCHARGING
        else:
            CUR_STATE = STATE_IDLE
    # print(cur_time)
    if last_tick_time + TICK_INTERVAL <= cur_time:
        last_tick_time = cur_time
        if CUR_STATE == STATE_DISCHARGING:
            discharge_tick()
        elif CUR_STATE == STATE_CHARGING:
            charge_tick()
        # print("{} - charge_level: {:4} charge_brightness: {:4}".format(CUR_STATE, charge_level, charge_brightness))
        new_progress = charge_level / MAX_CHARGE_LEVEL
        text_brightness.text = "Brightness: {:3} %".format(int((charge_brightness / MAX_CHARGE_BRIGHTNESS) * 100))
        new_width = int(board.DISPLAY.width * new_progress)
        rect.x = -240 + new_width

        if CUR_STATE == STATE_DISCHARGING:
            if charge_level > 0:
                led.duty_cycle = max(200, charge_brightness)
            else:
                CUR_STATE = STATE_IDLE
                charge_brightness = 0
        else:
            led.duty_cycle = 0
    old_a_val = cur_a_val
    old_b_val = cur_b_val
