#!/usr/bin/python
# --------------------------------------
#    ___  ___  _ ____
#   / _ \/ _ \(_) __/__  __ __
#  / , _/ ___/ /\ \/ _ \/ // /
# /_/|_/_/  /_/___/ .__/\_, /
#                /_/   /___/
#
#  lcd_16x2.py
#  20x4 LCD Test Script with
#  backlight control and text justification
#
# Author : Matt Hawkins
# Date   : 06/04/2015
#
# Modified  : Joshua Conrady
# Date      : 08/12/2019
#
# Modified for LCD 2004A for 8 bit transmission
#
# https://www.raspberrypi-spy.co.uk/
#
# --------------------------------------

# The wiring for the LCD is as follows:
# 1 : GND
# 2 : 5V
# 3 : Contrast (0-5V)*
# 4 : RS (Register Select)
# 5 : R/W (Read Write)       - GROUND THIS PIN
# 6 : Enable or Strobe
# 7 : Data Bit 0
# 8 : Data Bit 1
# 9 : Data Bit 2
# 10: Data Bit 3
# 11: Data Bit 4
# 12: Data Bit 5
# 13: Data Bit 6
# 14: Data Bit 7
# 15: LCD Backlight +5V**
# 16: LCD Backlight GND

# import
import RPi.GPIO as GPIO
import time

# Define GPIO to LCD mapping
LCD_RS = 23
LCD_E = 24
LCD_D0 = 2
LCD_D1 = 4
LCD_D2 = 3
LCD_D3 = 17
LCD_D4 = 18
LCD_D5 = 14
LCD_D6 = 15
LCD_D7 = 25

LCD_DATA_PINS = [
    LCD_D0, LCD_D1, LCD_D2,
    LCD_D3, LCD_D4, LCD_D5,
    LCD_D6, LCD_D7
    ]

# Define LCD commands (2004A)
LCD_BLANK = 0x01
LCD_RETURN = 0x02
LCD_CURSOR = 0x04
CURSOR_LEFT = 0x00
CURSOR_RIGHT = 0x02
LCD_DISPLAY = 0x08
DISPLAY_ON = 0x04
DISPLAY_OFF = 0x00
DISPLAY_CURSOR_ON = 0x02
DISPLAY_CURSOR_OFF = 0x00
DISPLAY_CURSOR_BLINK = 0x01
DISPLAY_CURSOR_SOLID = 0x00
LCD_DIPLAY_CURSOR_SHIFT = 0x10
DISPLAY_SHIFT = 0x08
CURSOR_SHIFT = 0x00
SHIFT_LEFT = 0x00
SHIFT_RIGHT = 0x04
LCD_FUNCTION_SET = 0x20
FUNCTION_8_BIT = 0x10
FUNCTION_4_BIT = 0x00
FUNCTION_1_LINE_DISPLAY = 0x00
FUNCTION_2_LINE_DISPLAY = 0x08
FUNCTION_5X8_FONT = 0x00
FUNCTION_5X11_FONT = 0x04
LCD_SET_DDRAM = 0x80

# Define LCD DDRAM lines
LCD_LINE_1 = 0x00
LCD_LINE_2 = 0x40
LCD_LINE_3 = 0x14
LCD_LINE_4 = 0x54

# Define LCD Styles
RIGHT_JUSTIFIED = 0
CENTERED = 1
LEFT_JUSTIFIED = 2

# Define some device constants
LCD_WIDTH = 20    # Maximum characters per line
LCD_RS_CHR = True
LCD_RS_CMD = False
LCD_E_ENABLE = True
LCD_E_DISABLE = False

# Timing constants
E_PULSE = 0.0005
E_DELAY = 0.0005


def lcd_blank():
    lcd_byte(LCD_BLANK, LCD_RS_CMD)


def lcd_init():

    GPIO.setmode(GPIO.BCM)       # Use BCM GPIO numbers
    GPIO.setup(LCD_E, GPIO.OUT, initial=GPIO.LOW)  # E
    GPIO.setup(LCD_RS, GPIO.OUT, initial=GPIO.LOW)  # RS
    for pin in LCD_DATA_PINS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)  # DBx

    # Initialise display
    lcd_byte(LCD_BLANK, LCD_RS_CMD)  # Blank the LCD
    lcd_byte(LCD_RETURN, LCD_RS_CMD)  # Return cursor to home
    lcd_byte(
        LCD_CURSOR  # Select cursor options
        | CURSOR_RIGHT,  # Set cursor motion to right to left
        LCD_RS_CMD)  # Send byte as command
    lcd_byte(
        LCD_DISPLAY  # Select display options
        | DISPLAY_ON  # Turn display on
        | DISPLAY_CURSOR_OFF  # Turn cursor on
        | DISPLAY_CURSOR_SOLID,  # Turn cursor blink off
        LCD_RS_CMD  # Send byte as command
        )
    lcd_byte(
        LCD_FUNCTION_SET  # Select function
        | FUNCTION_8_BIT  # Set MPL mode to 8 bit
        | FUNCTION_5X11_FONT
        # Set font to 5x11 dots (doesn't matter if double line format)
        | FUNCTION_2_LINE_DISPLAY,  # Set MPL to double line format
        LCD_RS_CMD  # Send byte as command
        )
    lcd_byte(LCD_BLANK, LCD_RS_CMD)  # Blank the LCD
    lcd_byte(LCD_RETURN, LCD_RS_CMD)  # Return cursor to home


def lcd_byte(bits, mode):
    # Send byte to data pins
    # bits = data
    # mode = True  for character
    #        False for command

    time.sleep(E_DELAY)
    reset_pins()
    time.sleep(E_DELAY)
    GPIO.output(LCD_RS, mode)  # RS
    time.sleep(E_DELAY)
    for index, pin in enumerate(LCD_DATA_PINS):
        GPIO.output(pin, get_bit(bits, index))
        time.sleep(E_DELAY)
    pulse_enable()
    time.sleep(E_DELAY)
    reset_pins()
    time.sleep(E_DELAY)


def reset_pins():
    for pin in LCD_DATA_PINS:
        time.sleep(E_DELAY)
        GPIO.output(pin, 0)
    time.sleep(E_DELAY)
    GPIO.output(LCD_E, 0)
    time.sleep(E_DELAY)
    GPIO.output(LCD_RS, 0)
    time.sleep(E_DELAY)


def pulse_enable():
    # Pulse the enable pin
    time.sleep(E_DELAY)
    GPIO.output(LCD_E, LCD_E_ENABLE)
    time.sleep(E_PULSE)
    GPIO.output(LCD_E, LCD_E_DISABLE)
    time.sleep(E_DELAY)


def get_bit(bits, index):
    # get the index'th bit of
    # the passed bits

    return bits & (1 << index) and 1 or 0


def lcd_string(message, line, style=LEFT_JUSTIFIED):
    # send as many bits as can fit on a line

    lcd_byte(line | LCD_SET_DDRAM, LCD_RS_CMD)

    if ((style == RIGHT_JUSTIFIED) and (len(message) < LCD_WIDTH)):
        for i in range(LCD_WIDTH - len(message)):
            lcd_byte(ord(" "), LCD_RS_CHR)
    elif (style == CENTERED and len(message) < LCD_WIDTH):
        for i in range((LCD_WIDTH - len(message)) / 2):
            lcd_byte(ord(" "), LCD_RS_CHR)
    for i in range(min(LCD_WIDTH, len(message))):
        lcd_byte(ord(message[i]), LCD_RS_CHR)
