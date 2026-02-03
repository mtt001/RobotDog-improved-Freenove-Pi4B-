# -*- coding: utf-8 -*-
"""
Application: Freenove Robot Dog Client - Network Communication Module
Authors   : MT & GitHub Copilot
Summary   : Handles TCP socket connections for command/video streaming, ball tracking, and face detection.

Revision History:
- 1.02 (2025-11-11): Add connection state check in send_data/receive_data to prevent AttributeError; add graceful video thread exit logging.
- 1.01 (2025-11-11): Add defensive socket cleanup with detailed debug logging; prevent AttributeError on 'connection.connection'; add safety checks for socket closure.
- 1.00: Original Client.py from Freenove Robot Dog Kit
"""
__version__ = "1.02 (2025-11-11)"
# =======================================================================================
import io
import copy
import socket
import struct
import threading
import time  # add this
from controllers.pid_controller import *
from Face import *
import numpy as np
from Thread import *
from PIL import Image
from controllers.dog_command_controller import COMMAND as cmd

class Client:
    def __init__(self):
        self.face = Face()
        self.pid=Incremental_PID(1,0,0.0025)
        self.tcp_flag=False
        self.video_flag=True
        self.ball_flag=False
        self.face_flag=False
        self.face_id = False
        self.image=''
        # Initialize socket references to None for safe cleanup
        self.client_socket1 = None  # Command socket
        self.client_socket = None   # Video socket
        self.connection = None      # Video stream file object
        self.video_thread_running = False  # NEW: Flag to control video thread lifecycle
        
    def turn_on_client(self,ip):
        # Create fresh socket instances for command and video channels
        self.client_socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #print (ip)
        print(f"... Connecting to Server IP {ip} on ports 5001 (Control) and 8001 (Video) ...")
        
    def turn_off_client(self):
        """
        Safely close all network connections with detailed logging.
        Prevents AttributeError by checking existence before accessing socket attributes.
        """
        try:
            print(f"[DEBUG] turn_off_client() called - tcp_flag: {self.tcp_flag}")
            
            # Signal video thread to stop gracefully
            self.video_thread_running = False
            
            # Close video stream file object first (prevents 'connection.connection' error)
            if hasattr(self, 'connection') and self.connection is not None:
                try:
                    print(f"[DEBUG] Closing video connection stream (type: {type(self.connection)})")
                    self.connection.close()
                    self.connection = None
                    print("[DEBUG] Video connection stream closed successfully")
                except Exception as e:
                    print(f"[DEBUG] Error closing video connection stream: {e}")
            
            # Close command socket (port 5001)
            if hasattr(self, 'client_socket1') and self.client_socket1 is not None:
                try:
                    print(f"[DEBUG] Closing command socket (type: {type(self.client_socket1)})")
                    self.client_socket1.close()
                    self.client_socket1 = None
                    print("[DEBUG] Command socket closed successfully")
                except Exception as e:
                    print(f"[DEBUG] Error closing command socket: {e}")
            
            # Close video socket (port 8001)
            if hasattr(self, 'client_socket') and self.client_socket is not None:
                try:
                    print(f"[DEBUG] Closing video socket (type: {type(self.client_socket)})")
                    self.client_socket.close()
                    self.client_socket = None
                    print("[DEBUG] Video socket closed successfully")
                except Exception as e:
                    print(f"[DEBUG] Error closing video socket: {e}")
                    
            print("[DEBUG] All sockets closed successfully")
            
        except AttributeError as e:
            # Catch cases where socket attributes don't exist (shouldn't happen with hasattr checks)
            print(f"[DEBUG] AttributeError during socket close: {e}")
        except Exception as e:
            # Catch any other unexpected errors during cleanup
            print(f"[DEBUG] Unexpected exception during socket close: {e}")
            
    def is_valid_image_4_bytes(self,buf): 
        bValid = True
        if buf[6:10] in (b'JFIF', b'Exif'):     
            if not buf.rstrip(b'\0\r\n').endswith(b'\xff\xd9'):
                bValid = False
        else:        
            try:  
                Image.open(io.BytesIO(buf)).verify() 
            except:  
                bValid = False
        return bValid
        
    def Looking_for_the_ball(self):
        MIN_RADIUS=10
        #red
        THRESHOLD_LOW = (0, 140, 140)
        THRESHOLD_HIGH = (5,255,255)

        img_filter = cv2.GaussianBlur(self.image.copy(), (3, 3), 0)
        img_filter = cv2.cvtColor(img_filter, cv2.COLOR_BGR2HSV)
        img_binary = cv2.inRange(img_filter.copy(), THRESHOLD_LOW, THRESHOLD_HIGH)
        img_binary = cv2.dilate(img_binary, None, iterations = 1)
        contours = cv2.findContours(img_binary.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        center = None
        radius = 0
        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            if M["m00"] > 0:
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                if radius < MIN_RADIUS:
                    center = None
        if center != None:
            cv2.circle(self.image, center, int(radius), (0, 255, 0))
            D=round(2700/(2*radius))  #CM
            x=self.pid.PID_compute(center[0])
            d=self.pid.PID_compute(D)
            if radius>15:
                if d < 20:
                        command=cmd.CMD_MOVE_BACKWARD+"#"+self.move_speed+'\n'
                        self.send_data(command)
                        #print (command)
                elif d > 30:
                        command=cmd.CMD_MOVE_FORWARD+"#"+self.move_speed+'\n'
                        self.send_data(command)
                        #print (command)
                else:
                    if x < 70:
                        command=cmd.CMD_TURN_LEFT+"#"+self.move_speed+'\n'
                        self.send_data(command)
                        #print (command)
                    elif x>270:
                        command=cmd.CMD_TURN_RIGHT+"#"+self.move_speed+'\n'
                        self.send_data(command)
                        #print (command)
                    else:
                        command=cmd.CMD_MOVE_STOP+"#"+self.move_speed+'\n'
                        self.send_data(command)
                        #print (command)
        else:
            command=cmd.CMD_MOVE_STOP+"#"+self.move_speed+'\n'
            self.send_data(command)
            #print (command)
            
    def receiving_video(self, ip):
        """
        Video streaming thread: connects to port 8001, reads JPEG frames with length prefix.
        Creates self.connection file object for binary stream reading.
        """
        stream_bytes = b' '
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Always use a fresh socket per attempt to avoid EINVAL after a failure
                if self.client_socket is not None:
                    try:
                        self.client_socket.close()
                    except Exception:
                        pass
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(5.0)

                print(f"[DEBUG] Connecting to video port 8001 (attempt {attempt + 1}/{max_retries})...")
                self.client_socket.connect((ip, 8001))
                self.connection = self.client_socket.makefile('rb')
                self.video_thread_running = True
                print("[DEBUG] Video socket connected, stream ready")
                break
            except Exception as e:
                print(f"[DEBUG] Video port connect failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait 1 second before retry
                else:
                    print("[ERROR] Failed to connect to video port after all retries")
                    return  # Exit thread

        while self.video_thread_running and self.connection is not None:
            try:
                # Read 4-byte length prefix for JPEG frame
                stream_bytes = self.connection.read(4)
                if not stream_bytes or len(stream_bytes) < 4:
                    # Connection closed or incomplete data
                    print("[DEBUG] Video stream ended (no data)")
                    break
                leng = struct.unpack('<L', stream_bytes[:4])
                # Read JPEG data based on length
                jpg = self.connection.read(leng[0])
                
                if self.is_valid_image_4_bytes(jpg):
                    if self.video_flag:
                        # Decode JPEG to OpenCV image
                        self.image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        
                        # Run ball tracking if enabled
                        if self.ball_flag and self.face_id == False:
                           self.Looking_for_the_ball()
                        # Run face detection if enabled
                        elif self.face_flag and self.face_id == False:
                            self.face.face_detect(self.image)
                            
                        self.video_flag = False
                        
            except Exception as e:
                # Only log error if thread should still be running (not during shutdown)
                if self.video_thread_running:
                    print(f"[DEBUG] Video receiving loop error: {e}")
                break
        
        print("[DEBUG] Video receiving thread exiting cleanly")
        
    def send_data(self, data):
        """Send command string to robot via command socket (port 5001)."""
        if self.tcp_flag and self.client_socket1 is not None:
            try:
                self.client_socket1.send(data.encode('utf-8'))
            except Exception as e:
                print(f"[DEBUG] send_data error: {e}")
        # Remove the else block to stop spam - silently ignore when not connected
        
    def receive_data(self):
        """Receive response data from robot command socket."""
        data = ""
        if self.tcp_flag and self.client_socket1 is not None:
            try:
                data = self.client_socket1.recv(1024).decode('utf-8')
            except Exception as e:
                print(f"[DEBUG] receive_data error: {e}")
        return data
