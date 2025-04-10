
#Library and module imports
from riposte import Riposte
from riposte.printer import Palette
import time
import sys
import RPi.GPIO as GPIO
import board
import adafruit_dht
import json
import smbus

#Banner that displays when the program is run
BANNER = """
                         #
                        # #   #    # #####  ####
                       #   #  #    #   #   #    #
                      #     # #    #   #   #    #
                      ####### #    #   #   #    #
                      #     # #    #   #   #    #
                      #     #  ####    #    ####

  #####
 #     # #####  ###### ###### #    # #    #  ####  #    #  ####  ######
 #       #    # #      #      ##   # #    # #    # #    # #      #
 #  #### #    # #####  #####  # #  # ###### #    # #    #  ####  #####
 #     # #####  #      #      #  # # #    # #    # #    #      # #
 #     # #   #  #      #      #   ## #    # #    # #    # #    # #
  #####  #    # ###### ###### #    # #    #  ####   ####   ####  ######

You must choose a growth model before automating
Enter the number of the command you want to execute
List of commands: \n 1. Choose Growth model \n 2. Automate \n 3. Test LEDs \n 99. Exit program \n
"""

#Assign name to the REPL, also assign prompt text and earlier defined banner
Greenhouse = Riposte(prompt="AutoGreenhouse:-$ ", banner = BANNER)


#variables
global GrowthModelPicked
GrowthModelPicked = False

#BCM pin definitions
MQ135Pin = 24
HygrometerPin = 23
LEDGasDetect = 10
LEDSoilDetect = 9
LEDLightHigh = 11
LEDLightLow = 5
LEDHumidHigh = 6
LEDHumidLow = 13
LEDTempHigh = 19
LEDTempLow = 26

#Set to BCM numbering and set pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(24, GPIO.IN)
GPIO.setup(23,GPIO.IN)
GPIO.setup(10, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(9, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(11, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(5, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(6, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(13, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(19, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(26, GPIO.OUT, initial=GPIO.LOW)
global DHT22Sensor
DHT22Sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)

#Other Functions

#prints error message in red text
def errormsg():
	errormsg = ("An error has occured. ")
	Greenhouse.print(Palette.RED.format(errormsg))


#Define sensor read functions for main command

def readDHT():
	temperature = 0
	humidity = 0

	#DHT sensors are hard to read due to timings or due to wiring, so this bit of code reads the sensor until values are given by it

	while temperature == 0:
		try:
			temperature = DHT22Sensor.temperature
			humidity = DHT22Sensor.humidity
			print("temp: ",temperature,"C")
			print("humidity: ",humidity,"%")
		except RuntimeError as err:
			print(err.args[0])
			DHTError = "re reading DHT sensor now. \n"
			Greenhouse.print(Palette.GREEN.format(DHTError))
		time.sleep(2.2)

	#Compare values to growth model ranges and activate or deactivate LEDs accordingly
	if temperature != 0:
		try:
			if humidity < humidity_lower:
				GPIO.output(LEDHumidLow, GPIO.HIGH)
				LHumid = "Humidity is too low! "
				Greenhouse.print(Palette.RED.format(LHumid))

			elif humidity > humidity_higher:
				GPIO.output(LEDHumidHigh, GPIO.HIGH)
				HHumid = "Humidity is too high! "
				Greenhouse.print(Palette.RED.format(HHumid))

			else:
				GPIO.output(LEDHumidHigh, GPIO.LOW)
				GPIO.output(LEDHumidLow, GPIO.LOW)
				RHumid = "Humidity is in range. "
				Greenhouse.print(Palette.GREEN.format(RHumid))



			if temperature < temperature_lower:
				GPIO.output(LEDTempLow, GPIO.HIGH)
				LTemp = "Temperature is too low! \n"
				Greenhouse.print(Palette.RED.format(LTemp))

			elif temperature > temperature_higher:
				GPIO.output(LEDTempHigh, GPIO.HIGH)
				HTemp = "Temperature is too high! \n"
				Greenhouse.print(Palette.RED.format(HTemp))

			else:
				GPIO.output(LEDTempHigh, GPIO.LOW)
				GPIO.output(LEDTempLow, GPIO.LOW)
				RTemp = "Temperature is in range. \n"
				Greenhouse.print(Palette.GREEN.format(RTemp))

		except RuntimeError as err:
			print(err.args[0])

def readBH1750():
	#assigned to 0x23 as the addr pin is connected to ground
	#also assign hex for other commands
	BHDevice = 0x23
	PowerDown = 0x00
	powerOn = 0x01
	Reset = 0x07
	bus = smbus.SMBus(1)

	#Convert 2 bytes of data taken to a decimal number
	def convert(data):
		result=(data[1] + (256 * data[0])) / 1.2
		return (result)

	#Read light in continuous high resolution mode 1. for 1 lux resolution. takes 120ms to read
	def ReadLight(addr=BHDevice):
		data = bus.read_i2c_block_data(addr, 0x10)
		return convert(data)

	#Read light and print light level, then compare to growth model ranges
	def RunLight():
		LightLevel = ReadLight()
		print("light level: " + format(LightLevel, '.2f') + " lx ")

		try:
			if LightLevel > light_higher:
				GPIO.output(LEDLightHigh, GPIO.HIGH)
				HLight = "Too much light! \n"
				Greenhouse.print(Palette.RED.format(HLight))

			elif LightLevel < light_lower:
				GPIO.output(LEDLightLow, GPIO.HIGH)
				LLight = "Not enough light! \n"
				Greenhouse.print(Palette.RED.format(LLight))

			else:
				GPIO.output(LEDLightLow, GPIO.LOW)
				GPIO.output(LEDLightHigh, GPIO.LOW)
				RLight = "Light level is in range. \n"
				Greenhouse.print(Palette.GREEN.format(RLight))
		except RuntimeError as err:
			print(err.args[0])

	try:
		RunLight()
	except RuntimeError as err:
		print(err.args[0])

#Function for reading Gas sensor, digital readings for this sensor are backwards so when
#TRUE is read, nothing is detected.
def readMQ135():
	try:
		if GPIO.input(MQ135Pin):
			LGas = ("C02 threshold not passed. \n")
			Greenhouse.print(Palette.GREEN.format(LGas))
			GPIO.output(LEDGasDetect, GPIO.LOW)
		else:
			HGas= ("C02 threshold passed! \n")
			Greenhouse.print(Palette.RED.format(HGas))
			GPIO.output(LEDGasDetect, GPIO.HIGH)

	except RuntimeError as err:
		print(err.args[0])

#Same here goes as goes for GAS sensor, TRUE means no water is detected.
def readSoil():
	try:
		if GPIO.input(HygrometerPin):
			LSoil = "Soil needs more water! \n"
			Greenhouse.print(Palette.RED.format(LSoil))
			GPIO.output(LEDSoilDetect, GPIO.HIGH)
		else:
			HSoil = "Soil has enough water. \n"
			Greenhouse.print(Palette.GREEN.format(HSoil))
			GPIO.output(LEDSoilDetect, GPIO.LOW)

	except RuntimeError as err:
		print(err.args[0])

#Sets the growth model
#setting commands with Riposte.command (in this case, Greenhouse.command) decorator, makes the REPL actionable.
@Greenhouse.command("1")
def growth():
	try:
		#prompts the user to pick a growth model
		print("Enter the number of the growth model you wish to use")
		GrowthModelInput = int(input(" 1. Strawberry \n 2. Paprika \n 3. Tomato \n "))

		#open json file
		with open('growth.json', 'r') as file:
			data = json.load(file)

		#search for matching ID number in file and then assign respective data
		#to global variables to be used in other functions
		matching = next((entry for entry in data if entry.get("id") == GrowthModelInput), None)
		if matching:
			print ("assigning growth model of id: ", matching["id"])
			global humidity_higher
			global humidity_lower
			global light_higher
			global light_lower
			global temperature_higher
			global temperature_lower
			humidity_higher = matching["Humidity_higher"]
			humidity_lower = matching["Humidity_lower"]
			light_higher = matching["Light_higher"]
			light_lower = matching["Light_lower"]
			temperature_higher = matching["Temperature_higher"]
			temperature_lower = matching["Temperature_lower"]
			global GrowthModelPicked
			GrowthModelPicked = True

			#Print out chosen ranges
			print (f"\nHumidity range: {humidity_lower} - {humidity_higher}%")
			print (f"Light range: {light_lower} - {light_higher} lux")
			print (f"Temperature range: {temperature_lower} - {temperature_higher} C\n")
		else:
			print ("no entry found")
	except:
		errormsg()




#Main command that reads sensors and adjusts LEDs
#Sets command using command decorator
@Greenhouse.command("2")
def main():
	if GrowthModelPicked:
		while True:
			try:
				#Loop that infinitely calls previously defined sensor read functions
				print ("-------------------------------------------\n")
				readDHT()
				time.sleep(1.5)
				readBH1750()
				time.sleep(1.5)
				readMQ135()
				time.sleep(1.5)
				readSoil()
				time.sleep(1.5)
				print ("-------------------------------------------\n")

			#As the reading is an infinite loop, closing down program is done by keyboard interrupt so this code handles a clean program exit
			except KeyboardInterrupt:
				print("Interrupted by user.\n shutting down program ")
				GPIO.cleanup()
				time.sleep(1)
				sys.exit(1)
			except RuntimeError as err:
				print(err.args[0])
				errormsg()
				GPIO.cleanup()
				time.sleep(1)
				sys.exit(1)
	else:
		#Doesn't let this command be run without picking a growth model
		growthError = ("You haven't picked a growth model yet! ")
		Greenhouse.print(Palette.RED.format(growthError))


#This command checks that none of the LEDs on the board a faulty and they all do light up when needed
@Greenhouse.command("3")
def LEDTest():
	pin = [10, 9, 11, 5, 6, 13, 19, 26]
	i = 0
	for i in pin:
		print("Pin ", i, " turned on")
		GPIO.output(i, GPIO.HIGH)
		time.sleep(0.5)
	i = 0
	for i in pin:
		print("Pin ", i , " turned off ")
		GPIO.output(i, GPIO.LOW)
		time.sleep(0.5)
	print("\nLED test complete ")
	time.sleep(1)

#Exit command that releases GPIO pins from use and then cleanly exits the program
@Greenhouse.command("99")
def exit():
	GPIO.cleanup()
	exit = ("Exiting program... ")
	Greenhouse.print(Palette.GREEN.format(exit))
	time.sleep(1)
	sys.exit(1)


#Runs the riposte session that allows the user to input commands and runs code.
Greenhouse.run()
