import time
import RPi.GPIO as GPIO
import json
import threading
import traceback
import lcd as LCD

from menu import MenuItem, Menu, MenuContext, MenuDelegate
from drinks import drink_list, drink_options

GPIO.setmode(GPIO.BCM)

LEFT_BTN_PIN = 12
LEFT_PIN_BOUNCE = 100

RIGHT_BTN_PIN = 16
RIGHT_PIN_BOUNCE = 100

UP_BTN_PIN = 21
UP_PIN_BOUNCE = 100

DOWN_BTN_PIN = 20
DOWN_PIN_BOUNCE = 100

FLOW_RATE = 60.0/100.0  # oz per second


class Bartender(MenuDelegate):
    def __init__(self):

        # allow button press
        self.running = False

        # initialize the LCD
        LCD.lcd_init()

        self.btn1Pin = LEFT_BTN_PIN
        self.btn2Pin = RIGHT_BTN_PIN
        self.btn3Pin = UP_BTN_PIN
        self.btn4Pin = DOWN_BTN_PIN

        # configure interrups for buttons
        GPIO.setup(self.btn1Pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.btn2Pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.btn3Pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.btn4Pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # load the pump configuration from file
        self.pump_configuration = Bartender.readPumpConfiguration()
        for pump in self.pump_configuration.keys():
            GPIO.setup(
                self.pump_configuration[pump]["pin"],
                GPIO.OUT,
                initial=GPIO.HIGH
                )

        print "Done initializing"

    @staticmethod
    def readPumpConfiguration():
        return json.load(open('pump_config.json'))

    @staticmethod
    def writePumpConfiguration(configuration):
        with open("pump_config.json", "w") as jsonFile:
            json.dump(configuration, jsonFile)

    def startInterrupts(self):
        GPIO.add_event_detect(
            self.btn1Pin,
            GPIO.FALLING,
            callback=self.left_btn,
            bouncetime=LEFT_PIN_BOUNCE
            )
        GPIO.add_event_detect(
            self.btn2Pin,
            GPIO.FALLING,
            callback=self.right_btn,
            bouncetime=RIGHT_PIN_BOUNCE
            )
        GPIO.add_event_detect(
            self.btn3Pin,
            GPIO.FALLING,
            callback=self.up_btn,
            bouncetime=UP_PIN_BOUNCE
            )
        GPIO.add_event_detect(
            self.btn4Pin,
            GPIO.FALLING,
            callback=self.down_btn,
            bouncetime=DOWN_PIN_BOUNCE
            )

    def stopInterrupts(self):
        GPIO.remove_event_detect(self.btn1Pin)
        GPIO.remove_event_detect(self.btn2Pin)
        GPIO.remove_event_detect(self.btn3Pin)
        GPIO.remove_event_detect(self.btn4Pin)

    def buildMenu(self, drink_list, drink_options):
        # create a new main menu
        m = Menu("Main Menu")

        # create a drinks menu
        drinks_menu = Menu("Drinks")

        # add drink options
        drink_opts = []
        for o in drink_options:
            drink_opts.append(
                MenuItem(
                    'drink',
                    o["name"],
                    {"ingredients": {o["value"]: 1}, "strong": o["alcohol"]}
                    )
                )
        for d in drink_list:
            drink_opts.append(
                MenuItem(
                    'drink',
                    d["name"],
                    {"ingredients": d["ingredients"]}
                    )
                )

        configuration_menu = Menu("Configure")

        # add pump configuration options
        pump_opts = []
        for p in sorted(self.pump_configuration.keys()):
            config = Menu(self.pump_configuration[p]["name"])

        # add fluid options for each pump
        for opt in drink_options:
            config.addOption(
                MenuItem(
                    'pump_selection',
                    opt["name"],
                    {"key": p, "value": opt["value"], "name": opt["name"]}
                    )
                )
        config.setParent(configuration_menu)
        pump_opts.append(config)

        # add pump menus to the configuration menu
        configuration_menu.addOptions(pump_opts)

        # adds an option that cleans all pumps to the configuration menu
        configuration_menu.addOption(MenuItem('clean', 'Clean'))
        configuration_menu.setParent(m)

        drinks_menu.addOptions(drink_opts)
        drinks_menu.setParent(m)
        self.filterDrinks(drinks_menu)

        m.addOption(drinks_menu)
        m.addOption(configuration_menu)

        # create a menu context
        self.menuContext = MenuContext(m, self)

    def filterDrinks(self, menu):
        """
        Removes any drinks that can't be handled by the pump configuration
        """
        for i in menu.options:
            if (i.type == "drink"):
                i.visible = False
                ingredients = i.attributes["ingredients"]
                presentIng = 0
                for ing in ingredients.keys():
                    for p in self.pump_configuration.keys():
                        if (ing == self.pump_configuration[p]["value"]):
                            presentIng += 1
                if (presentIng == len(ingredients.keys())):
                    i.visible = True
            elif (i.type == "menu"):
                self.filterDrinks(i)

    def menuItemClicked(self, menuItem):
        if (menuItem.type == "drink"):
            self.makeDrink(menuItem)
            return True
        elif(menuItem.type == "pump_selection"):
            value = menuItem.attributes["value"]
            self.pump_configuration[
                menuItem.attributes["key"]]["value"] = value
            Bartender.writePumpConfiguration(self.pump_configuration)
            return True
        elif(menuItem.type == "check"):
            return True
        elif(menuItem.type == "clean"):
            self.clean()
            return True
        return False

    def clean(self):
        waitTime = 20
        pumpThreads = []

        # cancel any button presses while the drink is being made
        # self.stopInterrupts()
        self.running = True

        for pump in self.pump_configuration.keys():
            pump_t = threading.Thread(
                target=self.pour,
                args=(self.pump_configuration[pump]["pin"], waitTime)
                )
            pumpThreads.append(pump_t)

        # start the pump threads
        for thread in pumpThreads:
            thread.start()

        # start the progress bar
        self.progressBar(waitTime)

        # wait for threads to finish
        for thread in pumpThreads:
            thread.join()

        # show the main menu
        self.menuContext.showMenu()

        # sleep for a couple seconds to make sure the interrupts
        # don't get triggered
        time.sleep(2)

        # reenable interrupts
        # self.startInterrupts()
        self.running = False

    def strongCheck(self, drink):
        s = Menu("This drink is strong")
        s.addOption(MenuItem('check', "continue"))
        s.setParent(self.menuContext.getCurrentMenu())
        self.menuContext.setMenu(s)
        self.menuContext.showMenu()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("keypress")

    def iceCheck(self, drink):
        i = Menu("Add Ice")
        i.addOption(MenuItem('check', "continue"))
        i.setParent(self.menuContext.getCurrentMenu())
        self.menuContext.setMenu(i)
        self.menuContext.showMenu()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("keypress")

    def addCheck(self, drink):
        a = Menu("Just add " + drink.add + "!")
        a.addOption(MenuItem('check', "done"))
        a.setParent(self.menuContext.getCurrentMenu())
        self.menuContext.setMenu(a)
        self.menuContext.showMenu()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("keypress")

    def strengthSelect(self, ingredients):
        str = Menu("Strength")
        str.addOption(MenuItem('check', "Weaker"))
        str.addOption(MenuItem('check', "Normal"))
        str.addOption(MenuItem('check', "Stronger"))
        str.setParent(self.menuContext.getCurrentMenu())
        self.menuContext.setMenu(str)
        self.menuContext.showMenu()

        newIngredients = ingredients.copy()

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("keypress")

        strength = self.menuContext.getSelection()

        alcModifier = 1
        nonAlcModifier = 1

        if (strength.name == "Weaker"):
            alcModifier = 0.8
            nonAlcModifier = 1.2
        elif (strength.name == "Stronger"):
            alcModifier = 1.2
            nonAlcModifier = 0.8
        else:
            return True

        for idx, ing in enumerate(newIngredients):
            for i in drink_options:
                if (ing.key == i.value and i.alcohol == 1):
                    newIngredients[idx] = ing * alcModifier
                else:
                    newIngredients[idx] = ing * nonAlcModifier
        return newIngredients

    def sizeSelect(self, ingredients):
        sizeM = Menu("Size Select")
        sizeM.addOption(MenuItem('check', "Shot"))
        sizeM.addOption(MenuItem('check', "4 oz"))
        sizeM.addOption(MenuItem('check', "6 oz"))
        sizeM.addOption(MenuItem('check', "8 oz"))
        sizeM.addOption(MenuItem('check', "10 oz"))
        sizeM.setParent(self.menuContext.getCurrentMenu())
        self.menuContext.setMenu(sizeM)
        self.menuContext.showMenu()

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("keypress")

        sizeOpt = self.menuContext.getSelection().name
        size = 0

        if (sizeOpt == "shot"):
            size = 1.5
        else:
            size = int(sizeOpt.split()[0])

        newIngredients = ingredients.copy()
        totalParts = 0

        for ing in ingredients:
            totalParts += ing
            for idx, ing in newIngredients:
                newIngredients[idx] = (ing / totalParts) * size

        return newIngredients

    def pour(self, pin, waitTime):
        GPIO.output(pin, GPIO.LOW)
        time.sleep(waitTime)
        GPIO.output(pin, GPIO.HIGH)

    def progressBar(self, waitTime):
        LCD.lcd_blank()
        LCD.lcd_byte(LCD.LCD_LINE_2 | LCD.LCD_SET_DDRAM, LCD.LCD_RS_CMD)
        block = 0xff
        for i in range(20):
            LCD.lcd_byte(block, LCD.LCD_RS_CHR)
            time.sleep(waitTime / 20)
        return True

    def makeDrink(self, drink):
        # cancel any button presses while the drink is being made
        # self.stopInterrupts()
        self.running = True

        # Parse the drink ingredients and spawn threads for pumps
        maxTime = 0
        pumpThreads = []

        ingredients = drink.attributes["ingredients"].copy()

        if (drink.strong == 1):
            self.strongCheck(drink)
        else:
            ingredients = self.strengthSelect(ingredients)
        if (drink.ice == 1):
            self.iceCheck(drink)

        ingredients = self.sizeSelect(ingredients)

        for ing in ingredients.keys():
            for pump in self.pump_configuration.keys():
                if ing == self.pump_configuration[pump]["value"]:
                    waitTime = ing * FLOW_RATE
                    if (waitTime > maxTime):
                        maxTime = waitTime
                    pump_t = threading.Thread(
                        target=self.pour,
                        args=(self.pump_configuration[pump]["pin"], waitTime)
                        )
                    pumpThreads.append(pump_t)

        # start the pump threads
        for thread in pumpThreads:
            thread.start()

        # start the progress bar
        self.progressBar(maxTime)

        # wait for threads to finish
        for thread in pumpThreads:
            thread.join()

        if (drink.add is not None):
            self.addCheck(drink)

        # show the main menu
        self.menuContext.retreat()

        # sleep for a couple seconds to make sure the interrupts
        # don't get triggered
        time.sleep(2)

        # reenable interrupts
        # self.startInterrupts()
        self.running = False

    def down_btn(self, ctx):
        if not self.running:
            self.menuContext.scroll_down()

    def up_btn(self, ctx):
        if not self.running:
            self.menuContext.scroll_up()

    def left_btn(self, ctx):
        if not self.running:
            self.menuContext.retreat()

    def right_btn(self, ctx):
        if not self.running:
            self.menuContext.select()

    def run(self):
        self.menuContext.showMenu()
        self.startInterrupts()

        # main loop
        try:
            while True:
                time.sleep(0.1)

        except KeyboardInterrupt:
            GPIO.cleanup()       # clean up GPIO on CTRL+C exit
        GPIO.cleanup()           # clean up GPIO on normal exit

        traceback.print_exc()


bartender = Bartender()
bartender.buildMenu(drink_list, drink_options)
bartender.run()
