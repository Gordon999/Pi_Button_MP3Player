#!/usr/bin/env python3
import RPi.GPIO as GPIO
import glob
import subprocess
import os, signal
import time
import random
from random import shuffle

# define GPIO pins used, first 10 for letters, second 10 for numbers
pins = (7,10,15,16,18,19,21,22,23,24,26,29,31,32,33,35,36,37,38,40)

# shuffle tracks played in continuous mode, set to 1 to shuffle
con_shuffle = 0

# buttons
stop = 8
shutdown  = 11
coinslot  = 13

# LEDS
LED1 = 12 # CABINET LED
LED2 = 5

# define letters
letters = ("A","B","C","D","E","F","G","H","I","J")

# setup GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
for count in range(0,len(pins)):
    GPIO.setup(pins[count],GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(stop,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(shutdown,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(coinslot,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED1,GPIO.OUT)
GPIO.setup(LED2,GPIO.OUT)
GPIO.output(LED1,GPIO.HIGH) # turn LED1 ON
GPIO.output(LED2,GPIO.LOW)  # turn LED2 OFF

# find tracks
tracks = glob.glob("/home/pi/Music/*.mp3")
tracks.sort()

# set starting variables
X = -1
Y = -1
coin_det = 0
time_start = 0
start = 0
B_pressed = 0
Con_Play = 0

print ("Insert a coin")

while True:

    # wait for a coin
    while GPIO.input(coinslot) == 1 and coin_det == 0:
        time.sleep (.25)
        if GPIO.input(shutdown) == 0:
            os.system("sudo shutdown -h now")

    # coin detected, start timer       
    if coin_det == 0:
        print ("Coin detected")
        time_start = time.time()
        GPIO.output(LED2,GPIO.HIGH) # turn LED2 ON
        coin_det = 1

    # if no activity for 60 seconds, cancel coin detected   
    if time.time() - time_start > 60 and X == -1:
        coin_det = 0
        GPIO.output(LED2,GPIO.LOW) # turn LED2 OFF
        print ("Sorry timed out, insert another coin !")
    
    time.sleep(0.1)
    if  GPIO.input(shutdown) == 0:
        print ("Goodbye!")
        os.system("sudo shutdown -h now")
        
    # check for a letter press
    if X == -1 and coin_det == 1:
        for A in range(0,int(len(pins)/2)):
            if GPIO.input(pins[A])== 0:
                X = A
                start = time.time()
                print ("Letter pressed")
                time_start = time.time()
                if X == 1:
                    print ("B Pressed")
                    B_pressed = 1
    if GPIO.input(pins[1]) == 1 and B_pressed == 1:
        B_pressed = 0
        print ("B Released")

    # no number pressed within 5 seconds of a letter, cancel letter
    # or continuous play mode if B pressed for > 5 seconds
    if X != -1 and time.time() - start > 5:
        if B_pressed == 0:
            X = -1
            GPIO.output(LED2,GPIO.HIGH) # turn LED2 ON
            print ("Timed out waiting for a number, choose again")
        else:
            print ("B Pressed > 5 secs")
            Con_Play = 1

    # no letter pressed within 5 seconds of a number, cancel number
    if Y != -1 and time.time() - start > 5:
        Y = -1
        GPIO.output(LED2,GPIO.HIGH) # turn LED2 ON
        print ("Timed out waiting for a letter, choose again")
            
    # check for a number press
    if Y == -1 and coin_det == 1:
        for B in range(int(len(pins)/2),len(pins)):
            if GPIO.input(pins[B])== 0:
                Y = (B - int(len(pins)/2))
                start = time.time()
                print ("Number pressed")
                time_start = time.time()
            
    # if letter AND number pressed play a song
    if X > -1 and Y > -1:
        GPIO.output(LED2,GPIO.LOW)                    # turn LED2 OFF
        # calculate track number from letter and number pressed
        Z = 10 * X + Y
        if Z < len(tracks):
            print ("Playing Track: ", letters[X] + str(Y+1), tracks[Z] )
            rpistr = "mplayer " + '"' + tracks[Z] + '"'
            p = subprocess.Popen(rpistr, shell=True, preexec_fn=os.setsid)
            # check if track still playing
            poll = p.poll()
            while poll == None:                       # track still playing
                GPIO.output(LED2,GPIO.LOW)            # turn LED2 OFF
                time.sleep(1)
                if  GPIO.input(stop) == 0:
                    print ("Track stopped")
                    os.killpg(p.pid, signal.SIGTERM)
                if  GPIO.input(shutdown) == 0:
                    GPIO.output(LED1,GPIO.LOW)        # turn LED1 OFF
                    print ("Goodbye!")
                    os.killpg(p.pid, signal.SIGTERM)
                    os.system("sudo shutdown -h now")
                    
                poll = p.poll()
            print ("Stopped Playing")
            coin_det = 0
            X = -1
            Y = -1
            print ("Insert another coin")
        else:
            print ("No track found")
            coin_det = 0
            X = -1
            Y = -1
            print ("Insert another coin")

    # Con_Play = 1 so continuous play mode...
    if Con_Play == 1:
        # shuffle tracks, if selected.
        nums = [0] * len(tracks)
        for q in range(0,len(tracks)):
            nums[q] = q
        if con_shuffle == 1:
            print ("Shuffled tracks")
            shuffle(nums)
        
        GPIO.output(LED2,GPIO.LOW)                      # turn LED2 OFF
        Z = 0
        while Con_Play == 1 :
            let = int(Z/10)
            num = (Z - (let*10)) + 1
            if Z < 100 and con_shuffle == 0:
                print ("Playing Track: ",str(Z+1),"of",str(len(tracks)),letters[let] + str(num), tracks[nums[Z]])
            else:
                print ("Playing Track: ",str(Z+1),"of",str(len(tracks)),tracks[nums[Z]])
            rpistr = "mplayer " + '"' + tracks[nums[Z]] + '"'
            p = subprocess.Popen(rpistr, shell=True, preexec_fn=os.setsid)
            # check if track still playing
            poll = p.poll()
            while poll == None:                         # track still playing
                GPIO.output(LED2,GPIO.LOW)              # turn LED2 OFF
                time.sleep(0.5)
                if  GPIO.input(pins[0]) == 0:           # Previous track     (A pressed)
                    print ("Previous Track...")
                    time.sleep(0.5)
                    os.killpg(p.pid, signal.SIGTERM)
                    Z -= 2
                    if Z < -1:
                        Z = len(tracks) + Z
                if  GPIO.input(pins[2]) == 0:           # Next Track         (C pressed)
                    print ("Next Track...")
                    time.sleep(0.5)
                    os.killpg(p.pid, signal.SIGTERM)
                if  GPIO.input(pins[3]) == 0:           # 10 Track Backwards (D pressed)
                    print ("Skip 10 Track backwards...")
                    time.sleep(0.5)
                    os.killpg(p.pid, signal.SIGTERM)
                    Z -= 11
                    if Z < -1:
                        Z = len(tracks) + Z
                if  GPIO.input(pins[4]) == 0:           # 10 Track Forward   (E pressed)
                    print ("Skip 10 Track forward...")
                    time.sleep(0.5)
                    os.killpg(p.pid, signal.SIGTERM)
                    if Z > len(tracks):
                        Z = Z - len(tracks)
                if  GPIO.input(stop) == 0:              # Exiting Continuous Play (if STOP pressed > 5 secs)
                    timer1 = time.time()
                    while GPIO.input(stop) == 0:
                        if time.time() - timer1 > 5:
                            if Con_Play == 1:
                                timer1 = time.time()
                                print ("Track stopped")
                                os.killpg(p.pid, signal.SIGTERM)
                                Con_Play = 0
                                Z = len(tracks)
                                print ("Exiting Continuous Play...")
                if  GPIO.input(shutdown) == 0:          # shutdown
                    GPIO.output(LED1,GPIO.LOW) 
                    print ("Goodbye!")
                    os.killpg(p.pid, signal.SIGTERM)
                    os.system("sudo shutdown -h now")
                poll = p.poll()
            Z += 1
            if Z > len(tracks) - 1:
                Z = 0
                if con_shuffle == 1:
                    print ("Shuffled tracks")
                    shuffle(nums)

        print ("Stopped Continuous Playing")
        B_pressed = 0
        Con_Play = 0
        coin_det = 0
        X = -1
        Y = -1
        tracks.sort()
        print ("Insert another coin")

            
