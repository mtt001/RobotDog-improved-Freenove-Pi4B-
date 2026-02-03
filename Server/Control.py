 # -*- coding: utf-8 -*-
"""
Control Module

Version: 1.1.0
Date: 2025-12-21
Author: Freenove

Description:
    Executes gait control, attitude balancing, and command dispatch for the
    Freenove Robot Dog. Includes relax/park behaviors, motion primitives, and
    integration with IMU, PID, and servo drivers.

Revision History:
    v1.1.1  (2026-02-02 20:31)    : Guard CMD_ATTITUDE when params are missing.
    1.1.0 (2025-12-21) - Handle CMD_STOP_PWM to disable all servo PWM outputs.
    1.0.0 (2024-12-21) - Initial motion control and balancing routines.
"""

import os
import signal; HEADLESS = os.getenv("SMARTDOG_HEADLESS") == "1"

import time
import math
import smbus
import copy
import threading
from IMU import *
from PID import *
import numpy as np
from Servo import *
from Command import COMMAND as cmd

# Temporary debug toggles (keep False for simpler/original behavior)
DEBUG_TURN = False

# If True, break out of long gait loops when a new command arrives.
# Set False to keep original behavior (complete current gait loop before switching).
PREEMPT_ON_NEW_COMMAND = False

# Optional movement debug
DEBUG_MOVE = False

# Command sequence debug (pairs with Server.DEBUG_COMMAND_SEQUENCE)
DEBUG_CMD_SEQ = False

# If the client alternates MOVE and STOP rapidly, treat STOP as "noise" for this long
# after the last motion command RX (helps joystick/key-repeat clients).
MOVE_HOLD_SEC = 0.35

# -----------------------------------------------------------------------------
# Over-usage ("3 min work / 1 min rest") protection
#
# Default: disabled (no forced rest). Enable if you want the robot to
# auto-relax after sustained activity.
#
# Semantics when enabled:
# - Active window: up to OVERUSE_ACTIVE_LIMIT_SEC seconds of servo-active time
# - Forced rest: next OVERUSE_REST_SEC seconds (servos relaxed)
# - After total OVERUSE_ACTIVE_LIMIT_SEC + OVERUSE_REST_SEC, counters reset
# -----------------------------------------------------------------------------
OVERUSE_PROTECTION_ENABLED = False
OVERUSE_ACTIVE_LIMIT_SEC = 180
OVERUSE_REST_SEC = 60
OVERUSE_RESET_SEC = OVERUSE_ACTIVE_LIMIT_SEC + OVERUSE_REST_SEC

class Control:
    def __init__(self):
        self.imu=IMU()
        self.servo=Servo()
        self.pid = Incremental_PID(0.5,0.0,0.0025)
        self.speed = 8
        self.height = 99
        self.timeout = 0
        self.move_flag = 0
        self.move_count = 0
        self.move_timeout = 0
        self.order = ['','','','','']
        self.order_seq = 0
        self.last_rx_seq = 0
        self.last_rx_raw = ''
        self.last_rx_ts = 0.0
        self.last_motion_order = ['','','','','']
        self.last_motion_seq = 0
        self.last_motion_rx_ts = 0.0
        self._last_exec_seq_logged = 0
        self.point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
        self.calibration_point = self.readFromTxt('point')
        self.angle = [[90,0,0],[90,0,0],[90,0,0],[90,0,0]]
        self.calibration_angle=[[0,0,0],[0,0,0],[0,0,0],[0,0,0]]
        self.relax_flag=True
        self.balance_flag=False
        self.attitude_flag=False
        self.over_usage_triggered=False  # Flag to prevent repeated RELAX TRIGGER #3
        self.Thread_conditiona=threading.Thread(target=self.condition)
        self.calibration()      # leg calibration on initialization based on saved points.
        print("🔵 [RELAX TRIGGER #1] Initialization - Disabling servos on startup")
        self.relax(True)    # Put the robot dog into relax state on initialization, disabling servos.

    def _ts_ms(self):
        now = time.time()
        return time.strftime('%H:%M:%S', time.localtime(now)) + f".{int((now % 1) * 1000):03d}"

    def _log_exec_if_new(self):
        if not DEBUG_CMD_SEQ:
            return
        seq = getattr(self, 'order_seq', 0)
        if not seq or seq == self._last_exec_seq_logged:
            return
        self._last_exec_seq_logged = seq
        try:
            params = self.order[1:]
        except Exception:
            params = []
        print(
            f"[EXEC {self._ts_ms()}] seq={seq} cmd={self.order[0]} params={params} relax={self.relax_flag} move_count={self.move_count:.1f}"
        )

    def _log_preempt(self, expected_cmd):
        if not DEBUG_CMD_SEQ:
            return
        actual = self.order[0] if isinstance(self.order, list) and len(self.order) else ''
        if actual == expected_cmd:
            return
        print(
            f"[PREEMPT {self._ts_ms()}] expected={expected_cmd} now={actual} seq_now={getattr(self,'order_seq',0)} last_rx_seq={getattr(self,'last_rx_seq',0)}"
        )

    def readFromTxt(self,filename):     # Read calibration points from file "point.txt"
        file1 = open(filename + ".txt", "r")
        list_row = file1.readlines()    # Read all lines , list_row is a list of strings, eg. ['23\t45\t67\n', '12\t34\t56\n']
        list_source = []
        for i in range(len(list_row)):      # Read each line
            column_list = list_row[i].strip().split("\t")   # Split by tab ('\t') to get each column value, 
            list_source.append(column_list)             # Append to list_source
        for i in range(len(list_source)):
            for j in range(len(list_source[i])):
                list_source[i][j] = int(list_source[i][j])
        file1.close()
        return list_source

    def saveToTxt(self,list, filename):
        file2 = open(filename + '.txt', 'w')
        for i in range(len(list)):
            for j in range(len(list[i])):
                file2.write(str(list[i][j]))
                file2.write('\t')
            file2.write('\n')
        file2.close()
        
    def coordinateToAngle(self,x,y,z,l1=23,l2=55,l3=55):
        a=math.pi/2-math.atan2(z,y)
        x_3=0
        x_4=l1*math.sin(a)
        x_5=l1*math.cos(a)
        l23=math.sqrt((z-x_5)**2+(y-x_4)**2+(x-x_3)**2)
        w=(x-x_3)/l23
        v=(l2*l2+l23*l23-l3*l3)/(2*l2*l23)
        b=math.asin(round(w,2))-math.acos(round(v,2))
        c=math.pi-math.acos(round((l2**2+l3**2-l23**2)/(2*l3*l2),2))
        a=round(math.degrees(a))
        b=round(math.degrees(b))
        c=round(math.degrees(c))
        return a,b,c
    
    def angleToCoordinate(self,a,b,c,l1=23,l2=55,l3=55):
        a=math.pi/180*a
        b=math.pi/180*b
        c=math.pi/180*c
        x=l3*math.sin(b+c)+l2*math.sin(b)
        y=l3*math.sin(a)*math.cos(b+c)+l2*math.sin(a)*math.cos(b)+l1*math.sin(a)
        z=l3*math.cos(a)*math.cos(b+c)+l2*math.cos(a)*math.cos(b)+l1*math.cos(a)
        return x,y,z
    
    def calibration(self):
        for i in range(4):
            self.calibration_angle[i][0],self.calibration_angle[i][1],self.calibration_angle[i][2]=self.coordinateToAngle(self.calibration_point[i][0],
                                                                                                                          self.calibration_point[i][1],
                                                                                                                          self.calibration_point[i][2])
        for i in range(4):
            self.angle[i][0],self.angle[i][1],self.angle[i][2]=self.coordinateToAngle(self.point[i][0],
                                                                                      self.point[i][1],
                                                                                      self.point[i][2])
        for i in range(4):
            self.calibration_angle[i][0]=self.calibration_angle[i][0]-self.angle[i][0]
            self.calibration_angle[i][1]=self.calibration_angle[i][1]-self.angle[i][1]
            self.calibration_angle[i][2]=self.calibration_angle[i][2]-self.angle[i][2]

    #---------   ⚠️ CRITICAL: Applies calibration here  ------------------------------
    """ Run() function to convert coordinates to angles and set servo angles with calibration applied 
        run() reads self.point[i][0..2] here (inverse kinematics input):
        Converts each leg’s (x,y,z) in self.point[i] into 3 joint angles via inverse kinematics (coordinateToAngle()).
        Applies calibration offsets (self.calibration_angle) and clamps angles.
        Sends the final angles to the servo driver using self.servo.setServoAngle(channel, angle) for each joint/leg.
    """
    def run(self): # 
        if self.checkPoint():
            try:
                for i in range(4):
                    self.angle[i][0],self.angle[i][1],self.angle[i][2]=self.coordinateToAngle(self.point[i][0],
                                                                                              self.point[i][1],
                                                                                              self.point[i][2])
                for i in range(2):
                    self.angle[i][0]=self.restriction(self.angle[i][0]+self.calibration_angle[i][0],0,180)
                    self.angle[i][1]=self.restriction(90-(self.angle[i][1]+self.calibration_angle[i][1]),0,180)
                    self.angle[i][2]=self.restriction(self.angle[i][2]+self.calibration_angle[i][2],0,180)
                    self.angle[i+2][0]=self.restriction(self.angle[i+2][0]+self.calibration_angle[i+2][0],0,180)
                    self.angle[i+2][1]=self.restriction(90+self.angle[i+2][1]+self.calibration_angle[i+2][1],0,180)
                    self.angle[i+2][2]=self.restriction(180-(self.angle[i+2][2]+self.calibration_angle[i+2][2]),0,180)
                for i in range(2):  # Left front leg: servos 4,5,6; Right front leg: servos 7,8,9
                    self.servo.setServoAngle(4+i*3,self.angle[i][0])    # hip servo at channel 4 and 7
                    self.servo.setServoAngle(3+i*3,self.angle[i][1])    # Knee servo at channel 3 and 6 (thigh servo)
                    self.servo.setServoAngle(2+i*3,self.angle[i][2])    # Ankle servo at channel 2 and 5 (shin servo)
                    self.servo.setServoAngle(8+i*3,self.angle[i+2][0])  # hip servo at channel 8 and 11
                    self.servo.setServoAngle(9+i*3,self.angle[i+2][1])  # Knee servo at channel 9 and 12 (thigh servo)
                    self.servo.setServoAngle(10+i*3,self.angle[i+2][2]) # Ankle servo at channel 10 and 13 (shin servo)
            except Exception as e:
                pass
        else:
            print("This coordinate point is out of the active range")
     # --------------------------------------------------------------   

    def checkPoint(self):
        flag=True
        leg_lenght=[0,0,0,0,0,0]  
        for i in range(4):
          leg_lenght[i]=math.sqrt(self.point[i][0]**2+self.point[i][1]**2+self.point[i][2]**2)
        for i in range(4         ):
          if leg_lenght[i] > 130 or leg_lenght[i] < 25:
            flag=False
        return flag
            
    def condition(self):
        while True:
            try:
                # If over-usage protection is disabled, never report "too tired".
                if not OVERUSE_PROTECTION_ENABLED and self.move_flag != 0:
                    self.move_flag = 0

                if time.time()-self.move_timeout > 60 and self.move_timeout!=0 and self.relax_flag==True:
                    self.move_count=0
                    self.move_timeout=time.time()

                # Normal operation unless over-usage protection is enabled and exceeded.
                if (not OVERUSE_PROTECTION_ENABLED) or (self.move_count < OVERUSE_ACTIVE_LIMIT_SEC):
                    # If a STOP arrives immediately after a motion command, keep moving briefly.
                    # This prevents "move a little then stop" when the client spams STOP between move packets.
                    if self.order[0] == cmd.CMD_MOVE_STOP:
                        try:
                            if (
                                self.last_motion_order
                                and self.last_motion_order[0] != ''
                                and (time.time() - self.last_motion_rx_ts) <= MOVE_HOLD_SEC
                            ):
                                if DEBUG_CMD_SEQ:
                                    age_ms = int((time.time() - self.last_motion_rx_ts) * 1000)
                                    print(
                                        f"[STOP-HOLD {self._ts_ms()}] ignoring STOP; using last_motion={self.last_motion_order[0]} age={age_ms}ms seq={self.last_motion_seq}"
                                    )
                                self.order = self.last_motion_order
                                self.order_seq = self.last_motion_seq
                        except Exception:
                            pass

                    if (time.time()-self.timeout)>5 and self.timeout!=0 and self.relax_flag==False and self.order[0] == '':
                        # TEMP: only show the message; do NOT enter power-save mode.
                        print("No commands for 5 seconds")
                        self.timeout=time.time()
                    if self.relax_flag==True and self.order[0] != ''  and self.order[0] !=cmd.CMD_RELAX and self.order[0] !=cmd.CMD_STOP_PWM: 
                        self.relax(False)
                        self.relax_flag=False
                        self.over_usage_triggered=False  # Reset flag when servos are activated
                    if self.attitude_flag==True and self.order[0] !=cmd.CMD_ATTITUDE and self.order[0] != '':
                        self.stop()   
                        self.attitude_flag=False  
                    if self.relax_flag==False: 
                        self.move_count+=time.time()-self.move_timeout
                        self.move_timeout=time.time()
                    if self.order[0]==cmd.CMD_MOVE_STOP:
                        self._log_exec_if_new()
                        self.order=['','','','','']
                        self.stop()

                    elif self.order[0]==cmd.CMD_MOVE_FORWARD:   # Move forward with speed = order[1], e.g., CMD_MOVE_FORWARD 5,  where 5 is the speed
                        self._log_exec_if_new()
                        try:
                            self.speed=int(self.order[1])
                        except Exception:
                            pass
                        if DEBUG_MOVE:
                            print(f"[MOVE] CMD_MOVE_FORWARD speed={self.speed}")
                        self.forWard()
                    
                    elif self.order[0]==cmd.CMD_MOVE_BACKWARD:
                        self._log_exec_if_new()
                        try:
                            self.speed=int(self.order[1])
                        except Exception:
                            pass
                        if DEBUG_MOVE:
                            print(f"[MOVE] CMD_MOVE_BACKWARD speed={self.speed}")
                        self.backWard()
                    elif self.order[0]==cmd.CMD_MOVE_LEFT:
                        self._log_exec_if_new()
                        try:
                            self.speed=int(self.order[1])
                        except Exception:
                            pass
                        self.setpLeft()
                    elif self.order[0]==cmd.CMD_MOVE_RIGHT:
                        self._log_exec_if_new()
                        try:
                            self.speed=int(self.order[1])
                        except Exception:
                            pass
                        self.setpRight()
                    elif self.order[0]==cmd.CMD_TURN_LEFT:
                        self._log_exec_if_new()
                        try:
                            self.speed=int(self.order[1])
                        except Exception:
                            pass
                        if DEBUG_TURN:
                            print(f"[TURN] CMD_TURN_LEFT speed={self.speed} relax_flag={self.relax_flag} move_count={self.move_count:.1f}")
                        self.turnLeft()
                    elif self.order[0]==cmd.CMD_TURN_RIGHT:
                        self._log_exec_if_new()
                        try:
                            self.speed=int(self.order[1])
                        except Exception:
                            pass
                        if DEBUG_TURN:
                            print(f"[TURN] CMD_TURN_RIGHT speed={self.speed} relax_flag={self.relax_flag} move_count={self.move_count:.1f}")
                        self.turnRight()
                    elif self.order[0]==cmd.CMD_RELAX:
                        self._log_exec_if_new()
                        # Behavior change (2026-01-16):
                        # CMD_RELAX is no longer a toggle.
                        # It always forces the robot into RELAX posture (servos stay powered).
                        if not self.relax_flag:
                            print("🟢 [RELAX] CMD_RELAX received - Entering RELAX posture (PWM ON)")
                        self.relax_flag=True
                        self.stop()
                        self.relax_posture()
                        self.order=['','','','','']
                    elif self.order[0]==cmd.CMD_STOP_PWM:
                        self._log_exec_if_new()
                        self.servo.stop_all_pwm()
                        self.order=['','','','','']
                    elif self.order[0]==cmd.CMD_HEIGHT:
                        self._log_exec_if_new()
                        self.upAndDown(int(self.order[1]))
                        self.order=['','','','','']
                    elif self.order[0]==cmd.CMD_HORIZON:
                        self._log_exec_if_new()
                        self.beforeAndAfter(int(self.order[1]))
                        self.order=['','','','','']
                    elif self.order[0]==cmd.CMD_ATTITUDE:
                        self._log_exec_if_new()
                        if len(self.order) >= 4:
                            self.attitude_flag=True
                            self.attitude(self.order[1],self.order[2],self.order[3])
                        else:
                            self.order=['','','','','']
                    elif self.order[0]==cmd.CMD_CALIBRATION:
                        self._log_exec_if_new()
                        self.move_count=0
                        if self.order[1]=="one":
                            self.calibration_point[0][0]=int(self.order[2])
                            self.calibration_point[0][1]=int(self.order[3])
                            self.calibration_point[0][2]=int(self.order[4])
                            self.calibration()
                            self.run()
                        elif self.order[1]=="two":
                            self.calibration_point[1][0]=int(self.order[2])
                            self.calibration_point[1][1]=int(self.order[3])
                            self.calibration_point[1][2]=int(self.order[4])
                            self.calibration()
                            self.run()
                        elif self.order[1]=="three":
                            self.calibration_point[2][0]=int(self.order[2])
                            self.calibration_point[2][1]=int(self.order[3])
                            self.calibration_point[2][2]=int(self.order[4])
                            self.calibration()
                            self.run()   
                        elif self.order[1]=="four":
                            self.calibration_point[3][0]=int(self.order[2])
                            self.calibration_point[3][1]=int(self.order[3])
                            self.calibration_point[3][2]=int(self.order[4])
                            self.calibration()
                            self.run()
                        elif self.order[1]=="save":
                            self.saveToTxt(self.calibration_point,'point')
                            self.stop()
                    elif self.order[0]==cmd.CMD_BALANCE and self.order[1]=='1':
                        Thread_IMU=threading.Thread(target=self.IMU6050)
                        Thread_IMU.start()
                        break
                else:
                    # Over-usage protection branch (enabled only).
                    if not self.over_usage_triggered:
                        print(
                            f"🔴 [RELAX TRIGGER #3] Over-Usage Protection - Robot active for {self.move_count:.0f}s "
                            f"(limit: {OVERUSE_ACTIVE_LIMIT_SEC}s); entering rest mode"
                        )
                        self.relax_flag=True
                        self.relax(True)
                        self.over_usage_triggered=True

                    if self.move_flag!=1:
                        self.move_flag=1

                    if self.move_count > OVERUSE_RESET_SEC:
                        self.move_count=0
                        self.move_flag=0
                        self.over_usage_triggered=False  # Reset flag when move_count resets

                    # Drop any queued motion while resting.
                    self.order=['','','','','']
            except Exception as e:
                print(e)
    def restriction(self,var,v_min,v_max):
        if var < v_min:
            return v_min
        elif var > v_max:
            return v_max
        else:
            return var            
    def map(self,value,fromLow,fromHigh,toLow,toHigh):  # Map value from one range to another
        return (toHigh-toLow)*(value-fromLow) / (fromHigh-fromLow) + toLow
    def changeCoordinates(self,move_order,X1=0,Y1=96,Z1=0,X2=0,Y2=96,Z2=0,pos=np.mat(np.zeros((3, 4)))):
        if move_order == 'turnLeft':  
            for i in range(2):
                self.point[2*i][0]=((-1)**(1+i))*X1+10
                self.point[2*i][1]=Y1
                self.point[2*i][2]=((-1)**(i))*Z1+((-1)**i)*10
                self.point[1+2*i][0]=((-1)**(1+i))*X2+10
                self.point[1+2*i][1]=Y2
                self.point[1+2*i][2]=((-1)**(1+i))*Z2+((-1)**i)*10
        elif move_order == 'turnRight': 
            for i in range(2):
                self.point[2*i][0]=((-1)**(i))*X1+10
                self.point[2*i][1]=Y1
                self.point[2*i][2]=((-1)**(1+i))*Z1+((-1)**i)*10
                self.point[1+2*i][0]=((-1)**(i))*X2+10
                self.point[1+2*i][1]=Y2
                self.point[1+2*i][2]=((-1)**(i))*Z2+((-1)**i)*10
        elif (move_order == 'height') or (move_order == 'horizon'):   
            for i in range(2):
                self.point[3*i][0]=X1+10
                self.point[3*i][1]=Y1
                self.point[1+i][0]=X2+10
                self.point[1+i][1]=Y2
        elif move_order == 'Attitude Angle': 
            for i in range(2):
                self.point[3-i][0]=pos[0,1+2*i]+10
                self.point[3-i][1]=pos[2,1+2*i]
                self.point[3-i][2]=pos[1,1+2*i]      
                self.point[i][0]=pos[0,2*i]+10
                self.point[i][1]=pos[2,2*i]
                self.point[i][2]=pos[1,2*i]

        else: #'backWard' 'forWard' 'setpRight' 'setpLeft'
            for i in range(2):
                self.point[i*2][0]=X1+10
                self.point[i*2][1]=Y1
                self.point[i*2+1][0]=X2+10
                self.point[i*2+1][1]=Y2
                self.point[i*2][2]=Z1+((-1)**i)*10   # ±10 for left/right offset
                self.point[i*2+1][2]=Z2+((-1)**i)*10

        # Apply updated coordinates for ALL move orders.
        # Previously, turnLeft/turnRight (and height/horizon/attitude) updated self.point
        # but did not call run(), so the servos never moved.
        self.run()   #===  ⚠️ CRITICAL: Applies calibration here  ===

    def backWard(self):
        for i in range(450,89,-self.speed):
            if PREEMPT_ON_NEW_COMMAND and self.order[0] != cmd.CMD_MOVE_BACKWARD:
                self._log_preempt(cmd.CMD_MOVE_BACKWARD)
                return
            X1=12*math.cos(i*math.pi/180)
            Y1=6*math.sin(i*math.pi/180)+self.height
            X2=12*math.cos((i+180)*math.pi/180)
            Y2=6*math.sin((i+180)*math.pi/180)+self.height
            if Y2 > self.height:
                Y2=self.height
            if Y1 > self.height:
                Y1=self.height
            self.changeCoordinates('backWard',X1,Y1,0,X2,Y2,0)
            #time.sleep(0.01)

    def forWard(self): # Move forward, Generate Motion Trajectory
        """ The forWard() method generates a gait by calculating foot positions in a circular arc:
            Loop generates foot coordinates: (X1, Y1, 0) for front legs, (X2, Y2, 0) for rear legs
            These are ideal/uncalibrated coordinates
            Each iteration calls changeCoordinates() which updates self.point[]
        """
        for i in range(90,451,self.speed):  # Move from 90 to 450 degrees with step of self.speed
            if PREEMPT_ON_NEW_COMMAND and self.order[0] != cmd.CMD_MOVE_FORWARD:
                self._log_preempt(cmd.CMD_MOVE_FORWARD)
                return
            X1=12*math.cos(i*math.pi/180)   # Front pari legs position, Calculate X1 based on cosine function
            Y1=6*math.sin(i*math.pi/180)+self.height    # (X1,Y1,0) for front legs
            X2=12*math.cos((i+180)*math.pi/180) # Rear pari legs position, Calculate X2 based on cosine function
            Y2=6*math.sin((i+180)*math.pi/180)+self.height  # (X2,Y2,0) for rear legs
            if Y2 > self.height:
                Y2=self.height
            if Y1 > self.height:
                Y1=self.height
            self.changeCoordinates('forWard',X1,Y1,0,X2,Y2,0)   # Each iteration calls this which updates calibrated self.point[] 
            #time.sleep(0.01)

    def turnLeft(self):
        for i in range(0,361,self.speed):
            if PREEMPT_ON_NEW_COMMAND and self.order[0] != cmd.CMD_TURN_LEFT:
                self._log_preempt(cmd.CMD_TURN_LEFT)
                return
            X1=3*math.cos(i*math.pi/180)
            Y1=8*math.sin(i*math.pi/180)+self.height
            X2=3*math.cos((i+180)*math.pi/180)
            Y2=8*math.sin((i+180)*math.pi/180)+self.height
            if Y2 > self.height:
                Y2=self.height
            if Y1 > self.height:
                Y1=self.height
            Z1=X1
            Z2=X2
            self.changeCoordinates('turnLeft',X1,Y1,Z1,X2,Y2,Z2)
            #time.sleep(0.01)
    
    def turnRight(self):
        for i in range(0,361,self.speed):
            if PREEMPT_ON_NEW_COMMAND and self.order[0] != cmd.CMD_TURN_RIGHT:
                self._log_preempt(cmd.CMD_TURN_RIGHT)
                return
            X1=3*math.cos(i*math.pi/180)
            Y1=8*math.sin(i*math.pi/180)+self.height
            X2=3*math.cos((i+180)*math.pi/180)
            Y2=8*math.sin((i+180)*math.pi/180)+self.height
            if Y2 > self.height:
                Y2=self.height
            if Y1 > self.height:
                Y1=self.height
            Z1=X1
            Z2=X2
            self.changeCoordinates('turnRight',X1,Y1,Z1,X2,Y2,Z2)  
            #time.sleep(0.01)
    def stop(self):
        p=[[10, self.height, 10], [10, self.height, 10], [10, self.height, -10], [10, self.height, -10]]
        for i in range(4):
            p[i][0]=(p[i][0]-self.point[i][0])/50
            p[i][1]=(p[i][1]-self.point[i][1])/50
            p[i][2]=(p[i][2]-self.point[i][2])/50
        for j in range(50):
            for i in range(4):
                self.point[i][0]+=p[i][0]
                self.point[i][1]+=p[i][1]
                self.point[i][2]+=p[i][2]
            self.run()
    def setpLeft(self):
        for i in range(90,451,self.speed):
            if PREEMPT_ON_NEW_COMMAND and self.order[0] != cmd.CMD_MOVE_LEFT:
                self._log_preempt(cmd.CMD_MOVE_LEFT)
                return
            Z1=10*math.cos(i*math.pi/180)
            Y1=5*math.sin(i*math.pi/180)+self.height
            Z2=10*math.cos((i+180)*math.pi/180)
            Y2=5*math.sin((i+180)*math.pi/180)+self.height
            if Y1 > self.height:
                Y1=self.height
            if Y2 > self.height:
                Y2=self.height
            self.changeCoordinates('setpLeft',0,Y1,Z1,0,Y2,Z2)
            #time.sleep(0.01)
    def setpRight(self):
        for i in range(450,89,-self.speed):
            if PREEMPT_ON_NEW_COMMAND and self.order[0] != cmd.CMD_MOVE_RIGHT:
                self._log_preempt(cmd.CMD_MOVE_RIGHT)
                return
            Z1=10*math.cos(i*math.pi/180)
            Y1=5*math.sin(i*math.pi/180)+self.height
            Z2=10*math.cos((i+180)*math.pi/180)
            Y2=5*math.sin((i+180)*math.pi/180)+self.height
            if Y1 > self.height:
                Y1=self.height
            if Y2 > self.height:
                Y2=self.height
            self.changeCoordinates('setpRight',0,Y1,Z1,0,Y2,Z2)
            #time.sleep(0.01)
            
    def relax_posture(self):
        """Move to RELAX posture while keeping servos powered (PWM continues).

        Behavior note (2026-01-16): CMD_RELAX uses this method so RELAX means
        "go to a safe/neutral posture" rather than "turn PWM off".
        """
        try:
            print("🔵 Moving servos to relaxed posture [55, 78, 0] (PWM stays ON)")
            target = [[55, 78, 0], [55, 78, 0], [55, 78, 0], [55, 78, 0]]
            step = [[0, 0, 0] for _ in range(4)]
            for i in range(4):
                step[i][0] = (self.point[i][0] - target[i][0]) / 50
                step[i][1] = (self.point[i][1] - target[i][1]) / 50
                step[i][2] = (self.point[i][2] - target[i][2]) / 50
            for _ in range(50):
                for i in range(4):
                    self.point[i][0] -= step[i][0]
                    self.point[i][1] -= step[i][1]
                    self.point[i][2] -= step[i][2]
                self.run()
            if self.move_timeout != 0:
                self.move_count += time.time() - self.move_timeout
                self.move_timeout = time.time()
        except Exception:
            pass

    # --- relax function to disable/enable servos for power saving ---
    def relax(self,flag=False):
        """Power-save wrapper.

        - flag=True : move to RELAX posture, then STOP all PWM outputs
        - flag=False: return to standing posture (PWM resumes during motion)
        """
        print("/n[DEBUG] RELAX Servos... relax flag:", flag) # Debug print
        if flag==True:
            self.relax_posture()
            # Power-saving: Stop all PWM outputs after reaching relax posture.
            time.sleep(0.1)
            self.servo.stop_all_pwm()
            print("💤 Power-save mode: All PWM outputs disabled to conserve battery")
        else:
            print("⚡ Waking up: Returning to standing position")
            self.stop()
            self.move_timeout=time.time()

    # ---- Height, Horizon, Attitude Control Functions ----            
    def upAndDown(self,var):
        self.height=var+99
        self.changeCoordinates('height',0,self.height,0,0,self.height,0)
    def beforeAndAfter(self,var):
        self.changeCoordinates('horizon',var,self.height,0,var,self.height,0)
    def attitude(self,r,p,y):
        r=self.map(int(r),-20,20,-10,10)
        p=self.map(int(p),-20,20,-10,10)
        y=self.map(int(y),-20,20,-10,10)
        pos=self.postureBalance(r,p,y,0)
        self.changeCoordinates('Attitude Angle',pos=pos)
    def IMU6050(self):
        self.balance_flag=True
        self.order=['','','','','']
        pos=self.postureBalance(0,0,0)
        self.changeCoordinates('Attitude Angle',pos=pos)
        time.sleep(2)
        self.imu.Error_value_accel_data,self.imu.Error_value_gyro_data=self.imu.average_filter()
        time.sleep(1)
        while True:
            self.move_count+=time.time()-self.move_timeout
            self.move_timeout=time.time()
            r,p,y=self.imu.imuUpdate()
            r=self.pid.PID_compute(r)
            p=self.pid.PID_compute(p)
            pos=self.postureBalance(r,p,0)
            self.changeCoordinates('Attitude Angle',pos=pos)
            if  (self.order[0]==cmd.CMD_BALANCE and self.order[1]=='0')or(self.balance_flag==True and self.order[0]!='')or(self.move_count>180):
                Thread_conditiona=threading.Thread(target=self.condition)
                Thread_conditiona.start()
                self.balance_flag=False
                break
    def postureBalance(self,r,p,y,h=1):
        b = 76
        w = 76
        l = 136
        if h!=0:
            h=self.height
        pos = np.mat([0.0,  0.0,  h ]).T 
        rpy = np.array([r,  p,  y]) * math.pi / 180 
        R, P, Y = rpy[0], rpy[1], rpy[2]
        rotx = np.mat([[ 1,       0,            0          ],
                     [ 0,       math.cos(R), -math.sin(R)],
                     [ 0,       math.sin(R),  math.cos(R)]])
        roty = np.mat([[ math.cos(P),  0,      -math.sin(P)],
                     [ 0,            1,       0          ],
                     [ math.sin(P),  0,       math.cos(P)]]) 
        rotz = np.mat([[ math.cos(Y), -math.sin(Y),  0     ],
                     [ math.sin(Y),  math.cos(Y),  0     ],
                     [ 0,            0,            1     ]])
        rot_mat = rotx * roty * rotz
        body_struc = np.mat([[ l / 2,  b / 2,  0],
                           [ l / 2, -b / 2,    0],
                           [-l / 2,  b / 2,    0],
                           [-l / 2, -b / 2,    0]]).T
        footpoint_struc = np.mat([[(l / 2),  (w / 2)+10,  self.height-h],
                                [ (l / 2), (-w / 2)-10,    self.height-h],
                                [(-l / 2),  (w / 2)+10,    self.height-h],
                                [(-l / 2), (-w / 2)-10,    self.height-h]]).T
        AB = np.mat(np.zeros((3, 4)))
        for i in range(4):
            AB[:, i] = pos + rot_mat * footpoint_struc[:, i] - body_struc[:, i]
        return (AB)
        
if __name__=='__main__':
    pass

        
   
