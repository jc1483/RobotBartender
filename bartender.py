import time
import RPi.GPIO as GPIO
import json
import threading
import traceback

from menu import MenuItem, Menu, Back, MenuContext, MenuDelegate
from drinks import drink_list, drink_options

GPIO.setmode(GPIO.BCM)

LEFT_BTN_PIN = 13
LEFT_PIN_BOUNCE = 1000

RIGHT_BTN_PIN = 5
RIGHT_PIN_BOUNCE = 2000

UP_BTN_PIN = 13
UP_PIN_BOUNCE = 1000

DOWN_BTN_PIN = 5
DOWN_PIN_BOUNCE = 2000

FLOW_RATE = 60.0/100.0  # oz per second


class Bartender(MenuDelegate):
	def __init__(self):
		self.running = False

		# set the oled screen height
		#self.screen_width = SCREEN_WIDTH
		#self.screen_height = SCREEN_HEIGHT

		self.btn1Pin = LEFT_BTN_PIN
		self.btn2Pin = RIGHT_BTN_PIN
		self.btn3Pin = UP_BTN_PIN
		self.btn4Pin = DOWN_BTN_PIN

	 	# configure interrups for buttons
	 	GPIO.setup(self.btn1Pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.btn2Pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.btn3Pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.btn4Pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		# configure screen
		#spi_bus = 0
		#spi_device = 0
		#gpio = gaugette.gpio.GPIO()
		#spi = gaugette.spi.SPI(spi_bus, spi_device)

		# Very important... This lets py-gaugette 'know' what pins to use in order to reset the display
		#self.led = gaugette.ssd1306.SSD1306(gpio, spi, reset_pin=OLED_RESET_PIN, dc_pin=OLED_DC_PIN, rows=self.screen_height, cols=self.screen_width) # Change rows & cols values depending on your display dimensions.
		#self.led.begin()
		#self.led.clear_display()
		#self.led.display()
		#self.led.invert_display()
		#time.sleep(0.5)
		#self.led.normal_display()
		#time.sleep(0.5)

		# load the pump configuration from file
		self.pump_configuration = Bartender.readPumpConfiguration()
		for pump in self.pump_configuration.keys():
			GPIO.setup(self.pump_configuration[pump]["pin"], GPIO.OUT, initial=GPIO.HIGH)

		print "Done initializing"

	@staticmethod
	def readPumpConfiguration():
		return json.load(open('pump_config.json'))

	@staticmethod
	def writePumpConfiguration(configuration):
		with open("pump_config.json", "w") as jsonFile:
			json.dump(configuration, jsonFile)

	def startInterrupts(self):
		GPIO.add_event_detect(self.btn1Pin, GPIO.FALLING, callback=self.left_btn, bouncetime=LEFT_PIN_BOUNCE)
		GPIO.add_event_detect(self.btn2Pin, GPIO.FALLING, callback=self.right_btn, bouncetime=RIGHT_PIN_BOUNCE)
		GPIO.add_event_detect(self.btn3Pin, GPIO.FALLING, callback=self.up_btn, bouncetime=UP_PIN_BOUNCE)
		GPIO.add_event_detect(self.btn4Pin, GPIO.FALLING, callback=self.down_btn, bouncetime=DOWN_PIN_BOUNCE)

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
			drink_opts.append(MenuItem('drink', o["name"], {"ingredients": o["value"]}))
		for d in drink_list:
			drink_opts.append(MenuItem('drink', d["name"], {"ingredients": d["ingredients"]}))

		configuration_menu = Menu("Configure")

		# add pump configuration options
		pump_opts = []
		for p in sorted(self.pump_configuration.keys()):
			config = Menu(self.pump_configuration[p]["name"])
			# add fluid options for each pump
			for opt in drink_options:
				# star the selected option
				selected = "*" if opt["value"] == self.pump_configuration[p]["value"] else ""
				config.addOption(MenuItem('pump_selection', opt["name"], {"key": p, "value": opt["value"], "name": opt["name"]}))
			config.setParent(configuration_menu)
			pump_opts.append(config)

		# add pump menus to the configuration menu
		configuration_menu.addOptions(pump_opts)
		# add a back button to the configuration menu
		configuration_menu.addOption(Back("Back"))
		# adds an option that cleans all pumps to the configuration menu
		configuration_menu.addOption(MenuItem('clean', 'Clean'))
		configuration_menu.setParent(m)

		drinks_menu.addOptions(drink_opts)
		drinks_menu.setParent(m)

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

	def selectConfigurations(self, menu):
		"""
		Adds a selection star to the pump configuration option
		"""
		for i in menu.options:
			if (i.type == "pump_selection"):
				key = i.attributes["key"]
				if (self.pump_configuration[key]["value"] == i.attributes["value"]):
					i.name = "%s %s" % (i.attributes["name"], "*")
				else:
					i.name = i.attributes["name"]
			elif (i.type == "menu"):
				self.selectConfigurations(i)

	def prepareForRender(self, menu):
		self.filterDrinks(menu)
		self.selectConfigurations(menu)
		return True

	def menuItemClicked(self, menuItem):
		if (menuItem.type == "drink"):
			self.makeDrink(menuItem)
			return True
		elif(menuItem.type == "pump_selection"):
			self.pump_configuration[menuItem.attributes["key"]]["value"] = menuItem.attributes["value"]
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
			pump_t = threading.Thread(target=self.pour, args=(self.pump_configuration[pump]["pin"], waitTime))
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

		# sleep for a couple seconds to make sure the interrupts don't get triggered
		time.sleep(2);

		# reenable interrupts
		# self.startInterrupts()
		self.running = False

	def displayMenuItem(self, menuItem):
		print menuItem.name
		self.led.clear_display()
		self.led.draw_text2(0,20,menuItem.name,2)
		self.led.display()

	def strongCheck(self, drink):
		s = Menu("Check Strength")
		strongMessage = "This drink is strong, are you sure you want to continue?"
		print strongMessage
		s.addOption(MenuItem('check', strongMessage))
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
		iceMessage = "Add ice to your glass if you haven't already!"
		print iceMessage
		i.addOption(MenuItem('check', iceMessage))
		i.setParent(self.menuContext.getCurrentMenu())
		self.menuContext.setMenu(i)
		self.menuContext.showMenu()
		try:
			while True:
				time.sleep(0.1)
		except KeyboardInterrupt:
			print("keypress")

	def addCheck(self, drink):
		a = Menu("Additions")
		addMessage = "Done! Just add " + drink.add
		print addMessage
		a.addOption(MenuItem('check', addMessage))
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
		interval = waitTime / 100.0
		for x in range(1, 101):
			self.led.clear_display()
			self.updateProgressBar(x, y=35)
			self.led.display()
			time.sleep(interval)

	def makeDrink(self, drink):
		# cancel any button presses while the drink is being made
		# self.stopInterrupts()
		self.running = True

		# Parse the drink ingredients and spawn threads for pumps
		maxTime = 0
		pumpThreads = []

		ingredients = drink.ingredients.copy()

		if (drink.strong == 1):
			self.strongCheck(drink)
		else:
			ingredients = self.strengthSelect(drink.ingredients)
		if (drink.ice == 1):
			self.iceCheck(drink)

		ingredients = self.sizeSelect(ingredients)

		for ing in ingredients.keys():
			for pump in self.pump_configuration.keys():
				if ing == self.pump_configuration[pump]["value"]:
					waitTime = ing * FLOW_RATE
					if (waitTime > maxTime):
						maxTime = waitTime
					pump_t = threading.Thread(target=self.pour, args=(self.pump_configuration[pump]["pin"], waitTime))
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
		self.menuContext.showMenu()

		# sleep for a couple seconds to make sure the interrupts don't get triggered
		time.sleep(2);

		# reenable interrupts
		# self.startInterrupts()
		self.running = False

	def down_btn(self, ctx):
		if not self.running:
			self.menuContext.decrease()

	def up_btn(self, ctx):
		if not self.running:
			self.menuContext.increase()

	def left_btn(self, ctx):
		if not self.running:
			self.menuContext.retreat()

	def right_btn(self, ctx):
		if not self.running:
			self.menuContext.select()

	def updateProgressBar(self, percent, x=15, y=15):
		height = 10
		width = self.screen_width-2*x
		for w in range(0, width):
			self.led.draw_pixel(w + x, y)
			self.led.draw_pixel(w + x, y + height)
		for h in range(0, height):
			self.led.draw_pixel(x, h + y)
			self.led.draw_pixel(self.screen_width-x, h + y)
			for p in range(0, percent):
				p_loc = int(p/100.0*width)
				self.led.draw_pixel(x + p_loc, h + y)

	def run(self):
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
