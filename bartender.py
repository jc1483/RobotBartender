import time
import RPi.GPIO as GPIO
import json
import threading
import traceback
import lcd as LCD

from menu import MenuItem, MenuLink, Menu, MenuContext, MenuDelegate
from drinks import drink_list, drink_options

GPIO.setmode(GPIO.BCM)

LEFT_BTN_PIN = 12
LEFT_PIN_BOUNCE = 500

RIGHT_BTN_PIN = 16
RIGHT_PIN_BOUNCE = 500

UP_BTN_PIN = 21
UP_PIN_BOUNCE = 500

DOWN_BTN_PIN = 20
DOWN_PIN_BOUNCE = 500

FLOW_RATE = 0.056/1.0  # oz per second


class Bartender(MenuDelegate):
    def __init__(self):

        # initialize drink attributes
        self.drink_attributes = {}

        # initialize main menu
        self.mainMenu = None

        # allow button press
        self.running = False

        # initialize the LCD
        self.lcdLayer = LCD.LCDLayer()

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
                    {
                        "ingredients": {o["value"]: 1},
                        "strong": o["alcohol"],
                        "ice": 0
                    }
                )
            )
        for d in drink_list:
            try:
                drink_opts.append(
                    MenuItem(
                        'drink',
                        d["name"],
                        {
                            "ingredients": d["ingredients"],
                            "strong": d["strong"],
                            "add": d["add"],
                            "ice": d["ice"]
                        }
                    )
                )
            except KeyError:
                drink_opts.append(
                    MenuItem(
                        'drink',
                        d["name"],
                        {
                            "ingredients": d["ingredients"],
                            "strong": d["strong"],
                            "ice": d["ice"]
                        }
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
        self.menuContext = MenuContext(m, self, self.lcdLayer)

    def setMainMenu(self, menu):
        self.mainMenu = menu

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
            self.menuContext.retreat()
            return True
        elif(menuItem.type == "pour"):
            self.pourDrink(menuItem.attributes)
            return True
        elif(menuItem.type == "clean"):
            self.clean()
            return True
        elif(menuItem.type == "menu_link"):
            if (menuItem.child is not None):
                try:
                    self.drink_attributes.update(menuItem.attributes)
                    print(self.drink_attributes)
                except TypeError:
                    print("menu item has no attributes")
                self.menuContext.currentMenu = menuItem.child
                self.menuContext.showMenu()
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

    def pour(self, pin, waitTime):
        GPIO.output(pin, GPIO.LOW)
        print(
            "Starting pour on pin " + str(pin) + " for " + str(waitTime)
            + " seconds")
        time.sleep(waitTime)
        GPIO.output(pin, GPIO.HIGH)
        print("Stopping pour on pin " + str(pin))

    def progressBar(self, waitTime):
        self.lcdLayer.lcd_blank()
        self.lcdLayer.lcd_string("Pouring", LCD.LCD_LINE_1, LCD.CENTERED)
        self.lcdLayer.lcd_byte(
            LCD.LCD_LINE_3
            | LCD.LCD_SET_DDRAM, LCD.LCD_RS_CMD)
        block = 0xff
        for i in range(20):
            self.lcdLayer.lcd_byte(block, LCD.LCD_RS_CHR)
            time.sleep(waitTime / 20)
        return True

    def makeDrink(self, drink):
        # Check for strength
        if (drink.attributes["strong"] == 1):
            strengthCheck = Menu("This drink is strong")
            strengthCheck.addOption(MenuLink(
                "Continue", strengthCheck, None, {"strength": "normal"}))
            strengthCheck.setParent(self.menuContext.currentMenu)
            self.menuContext.setMenu(strengthCheck)
        else:
            # Select strength
            strengthSelect = Menu("Select strength")
            strengthSelect.addOption(MenuLink(
                "Weak", strengthSelect, None, {"strength": "weak"}))
            strengthSelect.addOption(MenuLink(
                "Normal", strengthSelect, None, {"strength": "normal"}))
            strengthSelect.addOption(MenuLink(
                "Strong", strengthSelect, None, {"strength": "strong"}))
            strengthSelect.setParent(self.menuContext.currentMenu)
            self.menuContext.setMenu(strengthSelect)
        # Select size
        # create a size menu and point it back to strengthCheck or
        # strengthSelect
        sizeSelect = Menu("Select size")
        sizeSelect.setParent(self.menuContext.currentMenu)
        for links in self.menuContext.currentMenu.options:
            if links.type == "menu_link":
                links.setChild(sizeSelect)

        # add size options menus to strengthCheck and strengthSelect
        sizeSelect.addOption(MenuLink(
            "Shot", sizeSelect, None, {"size": "shot"}))
        sizeSelect.addOption(MenuLink(
            "4 oz", sizeSelect, None, {"size": "4 oz"}))
        sizeSelect.addOption(MenuLink(
            "6 oz", sizeSelect, None, {"size": "6 oz"}))
        sizeSelect.addOption(MenuLink(
            "8 oz", sizeSelect, None, {"size": "8 oz"}))
        sizeSelect.addOption(MenuLink(
            "10 oz", sizeSelect, None, {"size": "10 oz"}))
        sizeSelect.addOption(MenuLink(
            "12 oz", sizeSelect, None, {"size": "12 oz"}))

        # pour menu
        pour = Menu("Ready to pour?")
        pour.addOption(MenuItem("pour", "Continue", drink.attributes))

        # add ice
        if (drink.attributes["ice"] == 1):
            addIce = Menu("Add Ice")
            addIce.setParent(sizeSelect)
            pour.setParent(addIce)
            addIce.addOption(MenuLink(
                "Continue", addIce, pour))
            for option in sizeSelect.options:
                if option.type == "menu_link":
                    option.setChild(addIce)
        else:
            pour.setParent(sizeSelect)
            for option in sizeSelect.options:
                if option.type == "menu_link":
                    option.setChild(pour)

        # finally show the menu structure
        self.menuContext.showMenu()

    def pourDrink(self, drinkAttributes):
        self.running = True
        ingredients = drinkAttributes["ingredients"].copy()
        print("Ingredients: " + str(ingredients.keys()))
        size = self.drink_attributes["size"].split()[0]
        if size == "shot":
            size = 1.25
        else:
            size = float(size)
        print("Size = " + str(size) + " oz")
        strength = self.drink_attributes["strength"]
        print("Strength: " + str(strength))
        alcModifier = 1.0

        if (strength == "strong"):
            alcModifier = 1.3
        elif (strength == "weak"):
            alcModifier = 0.7

        # strength calculations
        totalIngredients = 0.0
        for ing in ingredients:
            totalIngredients += ingredients[ing]
            for opts in drink_options:
                if (ing == opts["value"]
                        and opts["alcohol"] == 1):
                    ingredients.update(
                        {ing: ingredients[ing] * 1.00 * alcModifier})

        print("Total parts: " + str(totalIngredients))

        # size calculations
        for ing in ingredients:
            ingredients.update(
                {ing: ingredients[ing] * size / totalIngredients})
            print(str(ingredients[ing]) + " oz of " + str(ing))

        maxTime = 0.00
        pumpThreads = []

        for ing in ingredients.keys():
            print("Looking for pump for ingredient: " + str(ing))
            found = False
            for pump in self.pump_configuration.keys():
                print("Checking pump " + str(pump))
                print(
                    "This pump is for: "
                    + str(self.pump_configuration[pump]["value"]))
                if ing == self.pump_configuration[pump]["value"]:
                    waitTime = (ingredients[ing] * 1.00) / FLOW_RATE
                    # oz/(oz/sec)=sec
                    if (waitTime > maxTime):
                        maxTime = waitTime
                    pump_t = threading.Thread(
                        target=self.pour,
                        args=(self.pump_configuration[pump]["pin"], waitTime)
                        )
                    print(
                        "Found pump for " + str(ing)
                        + ". Setting up pour for " + str(waitTime) + " sec")
                    pumpThreads.append(pump_t)
                    found = True
            if (not found):
                print("Could not find pump for ingredient: " + str(ing))

        print("Total pour time: " + str(maxTime))

        # start the pump threads
        for thread in pumpThreads:
            thread.start()

        # start the progress bar
        self.progressBar(maxTime)

        # wait for threads to finish
        for thread in pumpThreads:
            thread.join()

        # sleep for a couple seconds to make sure the interrupts
        # don't get triggered
        time.sleep(2)

        # reenable interrupts
        # self.startInterrupts()
        self.running = False

        # check for additions
        try:
            addMenu = Menu("Just add " + self.drink_attributes["add"])
            addMenu.addOption(MenuLink("Done", None, self.mainMenu))
            addMenu.setParent(self.mainMenu)
            self.menuContext.setMenu(addMenu)
        except KeyError:
            self.menuContext.setMenu(self.mainMenu)

        self.drink_attributes = {}
        self.menuContext.showMenu()

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
            self.lcdLayer.lcd_cleanup()       # clean up GPIO on CTRL+C exit
        self.lcdLayer.lcd_cleanup()           # clean up GPIO on normal exit

        traceback.print_exc()


bartender = Bartender()
bartender.buildMenu(drink_list, drink_options)
bartender.setMainMenu(bartender.menuContext.currentMenu)
bartender.run()
