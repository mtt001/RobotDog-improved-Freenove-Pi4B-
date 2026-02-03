# -*- coding: utf-8 -*-
"""
Freenove Robot Dog - Server GUI Application

File: main.py
Version: 1.0.0
Author: Freenove
Date Created: 2024

Description:
    Main entry point for the Freenove Robot Dog server GUI application.
    Handles server control and UI management for the robot dog system.

Version Control:
    v1.0.0 - Initial implementation
           - TCP server startup/shutdown UI
           - Video transmission support
           - Instruction receiving support
           - Thread management and cleanup

Revision History:
    Date        | Version | Author    | Changes
    ------------|---------|-----------|-----------------------------------------------
    2024-12-21  | 1.0.0   | Freenove  | Initial release

Dependencies:
    - PyQt5: GUI framework
    - threading: Thread management
    - ui_server: UI definitions
    - Server: Robot dog server control

Usage:
    python main.py [-t] [-n]
    Options:
        -t: Start TCP server automatically
        -n: Run without GUI
"""

import sys,getopt
from ui_server import Ui_server
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from Server import *

class MyWindow(QMainWindow,Ui_server):
    def __init__(self):
        self.user_ui=True
        self.start_tcp=False
        self.server=Server()
        self.parseOpt()
        if self.user_ui:
            self.app = QApplication(sys.argv)
            super(MyWindow,self).__init__()
            self.setupUi(self)
            self.pushButton_On_And_Off.clicked.connect(self.on_and_off_server)
            self.on_and_off_server()
        if self.start_tcp:
            self.server.turn_on_server()
            self.server.tcp_flag=True
            self.video=threading.Thread(target=self.server.transmission_video)
            self.video.start()
            self.instruction=threading.Thread(target=self.server.receive_instruction)
            self.instruction.start()
            
            if self.user_ui:
                self.pushButton_On_And_Off.setText('Off')
                self.states.setText('On')
                
    def parseOpt(self):
        self.opts,self.args = getopt.getopt(sys.argv[1:],"tn")
        for o,a in self.opts:
            if o in ('-t'):
                print ("Open TCP")
                self.start_tcp=True
            elif o in ('-n'):
                self.user_ui=False
                
    def on_and_off_server(self):
        if self.pushButton_On_And_Off.text() == 'On':
            self.pushButton_On_And_Off.setText('Off')
            self.states.setText('On')
            self.server.turn_on_server()
            self.server.tcp_flag=True
            self.video=threading.Thread(target=self.server.transmission_video)
            self.video.start()
            self.instruction=threading.Thread(target=self.server.receive_instruction)
            self.instruction.start()
        else:
            self.pushButton_On_And_Off.setText('On')
            self.states.setText('Off')
            self.server.tcp_flag=False
            try:
                stop_thread(self.video)
                stop_thread(self.instruction)
            except Exception as e:
                print(e)
            self.server.turn_off_server()
            print("close")
    def closeEvent(self,event):
        try:
            stop_thread(self.video)
            stop_thread(self.instruction)
        except:
            pass
        try:
            self.server.server_socket.shutdown(2)
            self.server.server_socket1.shutdown(2)
            self.server.turn_off_server()
        except:
            pass
        if self.user_ui:
            QCoreApplication.instance().quit()
        os._exit(0)
        
if __name__ == '__main__':
    myshow=MyWindow()
    if myshow.user_ui==True:
        myshow.show();  
        sys.exit(myshow.app.exec_())
    else:
        try:
            pass
        except KeyboardInterrupt:
            myshow.closeEvent(myshow)
