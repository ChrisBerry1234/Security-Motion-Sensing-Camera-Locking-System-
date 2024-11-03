#import libaries
import RPi.GPIO as GPIO
from gpiozero.pins.pigpio import PiGPIOFactory
from picamera import PiCamera
from mfrc522 import SimpleMFRC522
from gpiozero import Button, Buzzer, AngularServo
from RPLCD.i2c import CharLCD
from time import sleep, time
import threading
import gpiozero

#Setup for GPIO, RFID reader, camera, Servo, and I2C LCD
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
reader = SimpleMFRC522()
camera = PiCamera()
lcd = CharLCD('PCF8574', 0x27, auto_linebreaks=True)
gpiozero.Device.pin_factory = PiGPIOFactory()

#Define GPIO pins
GPIO.setup(21, GPIO.IN) #Motion Sensor Input
GPIO.setup(12, GPIO.OUT) #LED Input
button = Button(17)
buzzer = Buzzer(26)
servo = AngularServo(19, min_pulse_width = 0.0006, max_pulse_width = 0.0023)

#List of Authorized Users for RFID
AUTHORIZED_USERS = [1072948359468]

#Initialize varibale for tracking access attempts
Access_Attempts = 3
attempts = 0

def start_recording():
    camera.resolution = (640,480)
    camera.vflip = False
    camera.contrast = 10
    file_name = "/home/cberry1234/Securityvideos/video_" + str(time()) + ".h264"
    print("Start recording...")
    camera.start_recording(file_name)
   
def stop_recording():
    camera.stop_recording()
    print("Recording stopped.")
   
def display_message(timer):
    """Display a message with a countdown timer to exit."""
    lcd.clear()
    start_time = time()  # Record the current time when the function starts

    while True:
        # Display text messages on the LCD
        lcd.write_string("Do you want to\r\nEnter:")
        sleep(2)
        lcd.clear()
        lcd.write_string("Hold Button if\r\nYES")
        sleep(2)
        lcd.clear()
        lcd.write_string("Leave if NO")
        sleep(2)
        lcd.clear()
       
        # Exit the function if the button is pressed
        if button.is_pressed:
            lcd.clear()
            print("Button pressed, exiting display_message function.")
            break
       
        # Check if the timer has been reached
        if time() - start_time > timer:
            lcd.clear()
            print("Timeout reached, exiting display_message function.")
            break  # Exit the function after the timer

# Clear display at the end
lcd.clear()
   
def motion():
    Motion = GPIO.input(21)
    if Motion == 0:
        GPIO.output(12,0)#LED off
        return False #Function exits with return False
   
    elif Motion == 1:
        GPIO.output(12,1) #LED on
        sleep(3)
        return True #Function exits with return True
   
# Function to simulate a timer with a timeout
def timer(timeout=10):
    global id
    start_time = time()
    while time() - start_time < timeout:
        sleep(1)  # Optional: add a small delay to avoid busy-waiting
        if id:
            return id
        sleep(1)
    print('No Access Allowed')
   
def scan_tag():
    global id
    """Scans for a tag and exits if no tag is scanned within the timeout."""
    lcd.clear()
    lcd.write_string("Ok, Please scan\r\nyour tag")
    sleep(2)
    lcd.clear()
    lcd.write_string("Waiting for\r\nRFID...")
    # Attempt to read the tag
    id, text = reader.read()
   
def read_tag():
    global id
    id = None # For the else statement the name is already none, so there is no
    #need to specify the else statement because the progra
    print("Starting data processing...")
   
    # Create and start a thread that runs the timer function in the background
    #start the thread first because calling the input function blocks everything else from the program
    #This function starts the timer thread and waits for user input.
    #If the user does not provide a name, it waits for the timer thread to finish (using thread.join()) and then informs the user that no tag was entered, followed by a processing delay
    thread1 = threading.Thread(target=timer, args=(5,))
    thread1.start()
   
    thread2 = threading.Thread(target = scan_tag)
    thread2.start()
   
    #join(): This method blocks the main thread until the thread has completed.
    #It’s useful for waiting until a thread finishes before moving on in the code.
    thread1.join()
    #If the user provides their name before the timer runs out, they will be greeted.
    #If not, the program will inform them that no access is allowed after the timer expires.
    #if we do thread2.join, the program will not end until a tag is scanned
   
    if id:  # If a tag is read, return it
        print("Tag ID:", id)
        lcd.clear()
        return id
    else:
        stop_recording()
        print("You did not enter any tag\nRecording stopped")
        sleep(0.5)
        print("Data processing complete.")
        return None

def grant_access():
    stop_recording()
    lcd.clear()
    lcd.write_string("ACCESS GRANTED!!")
    sleep(2)
    lcd.clear()
    lcd.write_string("OPENING DOOR")
    servo.angle = 90  # Open door
    sleep(7) # Give User Time to Enter
    servo.angle = 0   # Close door
    sleep(2)

def tag_denied(attempts):
    lcd.write_string("NO ACCESS!\r\nPLEASE TRY AGAIN")
    while attempts <= Access_Attempts:
        id, text = reader.read()
        print("ID: %s\nText: %s" % (id,text))
   
        if id not in AUTHORIZED_USERS:
            lcd.clear()
            sleep(2)
            lcd.write_string("NO ACCESS!\r\nPLEASE TRY AGAIN")
            attempts += 1
           
        else:
            grant_access()
            break  # Exit loop if access is granted
           
        if attempts == Access_Attempts:
            lcd.clear()
            lcd.write_string("ACCESS DENIED\r\nMAX ATTEMPTS")
            return attempts # Exit function if max attempts reached
       
def alert_owner():
    lcd.write_string("TOO MANY!\r\nATTEMPTS")
    sleep(3)
    lcd.clear()
    lcd.write_string("ALERTING OWNER")
    for x in range(3):
        buzzer.beep(on_time=0.5, off_time=0.5, n=1)
        sleep(3)
       
   # Actions to perform after the loop completes
    stop_recording()
    buzzer.off()
    lcd.clear()
    sleep(4)

   
#Main Loop
while True:
   
    buzzer.off()
   
    #Checking for motion
    if motion() == False:
        continue
   
    else:
        display_message(timer= 20) #Motion equal true so display message to user

        if button.is_pressed:
            start_recording()
            id = read_tag()
         
            if id is None:
                lcd.clear()
                sleep(2)
                continue
               
            if id not in AUTHORIZED_USERS:
                attempts = tag_denied(attempts)
                if attempts == Access_Attempts:
                    alert_owner()
                    sleep(10)
             
            else:
                grant_access()
                attempt = 0
                sleep(2)
                break
