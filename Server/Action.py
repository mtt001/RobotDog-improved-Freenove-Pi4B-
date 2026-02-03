#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Action Demo Runner - Server Side

Version: 1.0.0
Date: 2025-12-23
Author: Freenove (server-side integration)

Description:
    Runs a sequence of robot dog demo motions directly on the server.
    Initializes all servos to 90°, plays per-demo entry cues (2 beeps + 2 LED flashes),
    announces each demo by name, and powers down PWM at the end (3 beeps + 3 flashes).

Revision History:
    1.0.0 (2025-12-23) - Added header, startup init, per-demo cues/announcements,
                         final PWM stop and completion cues.
"""

import math
import time
from Control import Control
from Servo import Servo
from Buzzer import Buzzer
from Led import Led
from Command import COMMAND as cmd
from testServo import ServoTester


class Action:
    def __init__(self):
        self.servo = Servo()
        self.control = Control()
        self.buzzer = self._init_buzzer()
        self.led = self._init_led()

        # Startup: center all servos to 90°
        self._center_all_servos()

    # ---------- helpers ----------
    def _init_buzzer(self):
        try:
            return Buzzer()
        except Exception:
            print("⚠️  Buzzer unavailable (sudo/GPIO needed). Continuing without beeps.")
            return None

    def _init_led(self):
        try:
            return Led()
        except Exception:
            print("⚠️  LED unavailable (sudo/WS281x needed). Continuing without LED.")
            return None

    def _beep(self, count=1, duration=0.1, pause=0.1):
        if self.buzzer is None:
            return
        try:
            for _ in range(count):
                self.buzzer.run('1')
                time.sleep(duration)
                self.buzzer.run('0')
                time.sleep(pause)
        except Exception:
            pass

    def _flash_led(self, count=1, on_time=0.2, off_time=0.2):
        if self.led is None:
            return
        try:
            for _ in range(count):
                self.led.light([cmd.CMD_LED, '1', '0', '0', '255'])
                time.sleep(on_time)
                self.led.light([cmd.CMD_LED, '0', '0', '0', '0'])
                time.sleep(off_time)
        except Exception:
            pass

    def _center_all_servos(self):
        for ch in range(16):
            self.servo.setServoAngle(ch, 90)
        time.sleep(0.5)

    def _announce_demo(self, name: str):
        print(f"\n▶️  Running demo: {name}")
        self._beep(count=2)
        self._flash_led(count=2)

    def _run_servo_exercise(self, delay=0.02):
        tester = ServoTester()
        tester.servo_exercise(delay=delay)
    def push_ups(self):
        xyz=[[0,50,0],[-100,23,0],[-100,23,0],[0,50,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.01)
        for i in range(4):
            for i in range(50,120,1):
                self.control.point[0][1]=i
                self.control.point[3][1]=i
                self.control.run()
                time.sleep(0.01)
            for i in range(120,50,-1):
                self.control.point[0][1]=i
                self.control.point[3][1]=i
                self.control.run()
                time.sleep(0.01)
        xyz=[[55,78,0],[55,78,0],[55,78,0],[55,78,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.01)
    def helloOne(self):  
        xyz=[[-20,120,-40],[50,105,0],[50,105,0],[0,120,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        x3=(80-self.control.point[3][0])/30
        y3=(23-self.control.point[3][1])/30
        z3=(0-self.control.point[3][2])/30
        for j in range(30):
            self.control.point[3][0]+=x3
            self.control.point[3][1]+=y3
            self.control.point[3][2]+=z3
            self.control.run()
            time.sleep(0.01)
        for i in range(2):
            for i in range(92,120,1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
            for i in range(120,60,-1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
            for i in range(60,92,1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
        xyz=[[55,78,0],[55,78,0],[55,78,0],[55,78,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        for i in range(90,130):
            self.servo.setServoAngle(15,i)
            time.sleep(0.02)
        for i in range(130,50,-1):
            self.servo.setServoAngle(15,i)
            time.sleep(0.02)
        for i in range(50,110):
            self.servo.setServoAngle(15,i)
            time.sleep(0.02)
    def helloTwo(self): 
        xyz=[[0,99,-30],[10,99,0],[10,99,0],[0,99,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)    
        x3=(80-self.control.point[3][0])/30
        y3=(23-self.control.point[3][1])/30
        z3=(0-self.control.point[3][2])/30
        for j in range(30):
            self.control.point[3][0]+=x3
            self.control.point[3][1]+=y3
            self.control.point[3][2]+=z3
            self.control.run()
            time.sleep(0.01)
            
        for i in range(2):
            for i in range(92,120,1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
            for i in range(120,60,-1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
            for i in range(60,92,1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
        self.control.stop()
        for i in range(10):
            self.control.setpLeft()
    def hand(self):
        xyz=[[-20,120,-20],[50,105,0],[50,105,0],[-20,120,20]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        
        for i in range(3):   
            x3=(100-self.control.point[3][0])/30
            y3=(40-self.control.point[3][1])/30
            z3=(10-self.control.point[3][2])/30
            for j in range(30):
                self.control.point[3][0]+=x3
                self.control.point[3][1]+=y3
                self.control.point[3][2]+=z3
                self.control.run()
                time.sleep(0.001)
                
        
            x3=(-20-self.control.point[3][0])/30
            y3=(120-self.control.point[3][1])/30
            z3=(20-self.control.point[3][2])/30
            for j in range(30):
                self.control.point[3][0]+=x3
                self.control.point[3][1]+=y3
                self.control.point[3][2]+=z3
                self.control.run()
                time.sleep(0.001)
            
            x0=(100-self.control.point[0][0])/30
            y0=(40-self.control.point[0][1])/30
            z0=(-10-self.control.point[0][2])/30
            for j in range(30):
                self.control.point[0][0]+=x0
                self.control.point[0][1]+=y0
                self.control.point[0][2]+=z0
                self.control.run()
                time.sleep(0.001)
            x0=(-20-self.control.point[0][0])/30
            y0=(120-self.control.point[0][1])/30
            z0=(-20-self.control.point[0][2])/30
            for j in range(30):
                self.control.point[0][0]+=x0
                self.control.point[0][1]+=y0
                self.control.point[0][2]+=z0
                self.control.run()
                time.sleep(0.001)
        xyz=[[55,78,0],[55,78,0],[55,78,0],[55,78,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        
    def coquettish(self):
        xyz=[[80,80,0],[-30,120,0],[-30,120,0],[80,80,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        for _ in range(3):
            xyz=[[80,80,-30],[-30,120,30],[-30,120,30],[80,80,-30]]
            for i in range(4):
                xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
                xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
                xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
            for j in range(30):
                for i in range(4):
                    self.control.point[i][0]+=xyz[i][0]
                    self.control.point[i][1]+=xyz[i][1]
                    self.control.point[i][2]+=xyz[i][2]
                self.control.run()
                time.sleep(0.02)
            
            xyz=[[80,80,30],[-30,120,-30],[-30,120,-30],[80,80,30]]
            for i in range(4):
                xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
                xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
                xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
            for j in range(30):
                for i in range(4):
                    self.control.point[i][0]+=xyz[i][0]
                    self.control.point[i][1]+=xyz[i][1]
                    self.control.point[i][2]+=xyz[i][2]
                self.control.run()
                time.sleep(0.02)
                
    def swim(self):
        z=100*math.cos(45/180*math.pi)+23
        x=100*math.sin(45/180*math.pi)
        xyz=[[-x,0,z],[-78,0,100],[-78,0,-100],[-x,0,-z]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        for i in range(3):
            for i in range(45,-45,-1):
                z=100*math.cos(i/180*math.pi)+23
                x=100*math.sin(i/180*math.pi)
                xyz=[[-x,0,z],[-78,0,100],[-78,0,-100],[-x,0,-z]]
                for i in range(4):
                    xyz[i][0]=(xyz[i][0]-self.control.point[i][0])
                    xyz[i][1]=(xyz[i][1]-self.control.point[i][1])
                    xyz[i][2]=(xyz[i][2]-self.control.point[i][2])
                for i in range(4):
                    self.control.point[i][0]+=xyz[i][0]
                    self.control.point[i][1]+=xyz[i][1]
                    self.control.point[i][2]+=xyz[i][2]
                self.control.run()
            for i in range(-45,45,1):
                z=100*math.cos(i/180*math.pi)+23
                x=100*math.sin(i/180*math.pi)
                xyz=[[-x,0,z],[-78,0,100],[-78,0,-100],[-x,0,-z]]
                for i in range(4):
                    xyz[i][0]=(xyz[i][0]-self.control.point[i][0])
                    xyz[i][1]=(xyz[i][1]-self.control.point[i][1])
                    xyz[i][2]=(xyz[i][2]-self.control.point[i][2])
                for i in range(4):
                    self.control.point[i][0]+=xyz[i][0]
                    self.control.point[i][1]+=xyz[i][1]
                    self.control.point[i][2]+=xyz[i][2]
                self.control.run()
        xyz=[[55,78,0],[55,78,0],[55,78,0],[55,78,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        time.sleep(1)
        
    def yoga(self):
        xyz=[[55,78,0],[55,78,0],[55,78,0],[55,78,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
            
        y=100*math.cos(45/180*math.pi)+23
        x=100*math.sin(45/180*math.pi)
        xyz=[[-x,y,0],[0,0,123],[0,0,-123],[-x,y,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run() 
            time.sleep(0.02)
            
        for i in range(3):
            for i in range(45,-45,-1):
                y=100*math.cos(i/180*math.pi)+23
                x=100*math.sin(i/180*math.pi)
                xyz=[[-x,y,0],[0,0,123],[0,0,-123],[-x,y,0]]
                for i in range(4):
                    xyz[i][0]=(xyz[i][0]-self.control.point[i][0])
                    xyz[i][1]=(xyz[i][1]-self.control.point[i][1])
                    xyz[i][2]=(xyz[i][2]-self.control.point[i][2])
                for i in range(4):
                    self.control.point[i][0]+=xyz[i][0]
                    self.control.point[i][1]+=xyz[i][1]
                    self.control.point[i][2]+=xyz[i][2]
                self.control.run() 
            for i in range(-45,45,1):
                y=100*math.cos(i/180*math.pi)+23
                x=100*math.sin(i/180*math.pi)
                xyz=xyz=[[-x,y,0],[0,0,123],[0,0,-123],[-x,y,0]]
                for i in range(4):
                    xyz[i][0]=(xyz[i][0]-self.control.point[i][0])
                    xyz[i][1]=(xyz[i][1]-self.control.point[i][1])
                    xyz[i][2]=(xyz[i][2]-self.control.point[i][2])
                for i in range(4):
                    self.control.point[i][0]+=xyz[i][0]
                    self.control.point[i][1]+=xyz[i][1]
                    self.control.point[i][2]+=xyz[i][2]
                self.control.run() 
        xyz=[[55,78,0],[55,78,0],[55,78,0],[55,78,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        time.sleep(1)
    
        
if __name__=='__main__':
    action = Action()
    time.sleep(1)

    # Run selected demos (all enabled by default)
    demos = [
        ("servo_exercise", lambda: action._run_servo_exercise(delay=0.01)),
        ("push_ups", action.push_ups),
        ("helloOne", action.helloOne),
        ("hand", action.hand),
        ("coquettish", action.coquettish),
        ("swim", action.swim),
        ("yoga", action.yoga),
        ("helloTwo", action.helloTwo),
    ]

    try:
        import threading
        stop_event = threading.Event()

        def listen_for_q():
            while not stop_event.is_set():
                try:
                    line = input()
                except EOFError:
                    break
                if line.strip().lower() == 'q':
                    stop_event.set()

        threading.Thread(target=listen_for_q, daemon=True).start()

        # Show demo list
        print("\nDemo order:")
        for idx, (name, _) in enumerate(demos, start=1):
            print(f"  {idx}. {name}")

        # Loop demos continuously until 'q'
        while not stop_event.is_set():
            for idx, (name, demo_fn) in enumerate(demos, start=1):
                if stop_event.is_set():
                    break
                print(f"\n▶️  Demo {idx}: {name}")
                action._beep(count=2)
                action._flash_led(count=2)
                demo_fn()
                time.sleep(3)

        # Completion cues
        action._beep(count=3)
        action._flash_led(count=3)
    finally:
        # Always power down PWM at the end
        action.servo.stop_all_pwm()
        print("All servo PWM outputs disabled (stop_all_pwm)")
        
