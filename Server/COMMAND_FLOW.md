# Command Receiving & Execution Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT (Windows/PC)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Main.py - PyQt5 GUI Application                          │  │
│  │  ├─ Button/Slider Events                                  │  │
│  │  │  └─ Triggers Methods (forward, backward, etc)          │  │
│  │  └─ Sends Commands via send_data()                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                      │
│                            ↓ (encode as UTF-8 string)            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Command Format: "CMD_NAME#param1#param2\n"              │  │
│  │  Examples:                                                 │  │
│  │  - "CMD_MOVE_FORWARD#50\n"                                │  │
│  │  - "CMD_MOVE_STOP#0\n"                                    │  │
│  │  - "CMD_BUZZER#on\n"                                      │  │
│  │  - "CMD_CALIBRATION#one#0#99#10\n"                        │  │
│  │  - "CMD_HEIGHT#10\n"                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                 │
                    TCP Socket Connection
                    Port 5001 (Instruction)
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                   SERVER (Raspberry Pi)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Server.py - receive_instruction()                        │  │
│  │  ├─ Listens on port 5001                                  │  │
│  │  ├─ Receives command string                               │  │
│  │  ├─ Split by '\n' to get command array                   │  │
│  │  └─ Split each command by '#' to parse components        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                      │
│                            ↓ (Parse command)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Command Routing (Server.py lines 183-225)                │  │
│  │  ├─ CMD_BUZZER          → buzzer.run(data[1])            │  │
│  │  ├─ CMD_LED/LED_MOD     → threading + led.light(data)    │  │
│  │  ├─ CMD_HEAD            → servo.setServoAngle(15, ...)   │  │
│  │  ├─ CMD_SONIC           → Send distance response         │  │
│  │  ├─ CMD_POWER           → Send battery voltage           │  │
│  │  ├─ CMD_WORKING_TIME    → Send working time              │  │
│  │  └─ Other Commands      → control.order = data           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                      │
│                            ↓ (For movement commands)              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Control.py - Thread_condition (Executes loop)            │  │
│  │  Checks control.order every iteration                     │  │
│  │  ├─ CMD_MOVE_FORWARD    → forWard()                       │  │
│  │  ├─ CMD_MOVE_BACKWARD   → backWard()                      │  │
│  │  ├─ CMD_MOVE_LEFT       → setpLeft()                      │  │
│  │  ├─ CMD_MOVE_RIGHT      → setpRight()                     │  │
│  │  ├─ CMD_TURN_LEFT       → turnLeft()                      │  │
│  │  ├─ CMD_TURN_RIGHT      → turnRight()                     │  │
│  │  ├─ CMD_MOVE_STOP       → stop()                          │  │
│  │  ├─ CMD_RELAX           → relax(True/False)               │  │
│  │  ├─ CMD_HEIGHT          → upAndDown(angle)                │  │
│  │  ├─ CMD_HORIZON         → beforeAndAfter(angle)           │  │
│  │  ├─ CMD_ATTITUDE        → attitude(pitch,yaw,roll)        │  │
│  │  ├─ CMD_CALIBRATION     → calibration()                   │  │
│  │  └─ CMD_BALANCE         → IMU6050()                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                      │
│                            ↓ (Execute motion)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Hardware Execution                                        │  │
│  │  ├─ Servo.py → setServoAngle(channel, angle)              │  │
│  │  ├─ Led.py → light(data)                                  │  │
│  │  ├─ Buzzer.py → run(type)                                 │  │
│  │  ├─ IMU.py → angle measurements                           │  │
│  │  └─ Ultrasonic.py → getDistance()                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Command Processing Flow

### 1. **Client Side - Command Sending** (Main.py)

```python
# Example: Button Forward Click
def forward(self):
    command = cmd.CMD_MOVE_FORWARD + "#" + self.client.move_speed + '\n'
    # Result: "CMD_MOVE_FORWARD#50\n"
    self.client.send_data(command)

# Example: Calibration
def calibration_save(self):
    command = cmd.CMD_CALIBRATION + "#one#0#99#10\n"
    # Result: "CMD_CALIBRATION#one#0#99#10\n"
    self.client.send_data(command)
```

### 2. **Server Side - Command Reception** (Server.py lines 145-176)

```python
def receive_instruction(self):
    # Accepts client connection on port 5001
    self.connection1, self.client_address1 = self.server_socket1.accept()
    
    while True:
        # Receive command string (UTF-8 encoded)
        allData = self.connection1.recv(1024).decode('utf-8')
        
        # Split by newlines to handle multiple commands
        cmdArray = allData.split('\n')
        
        for oneCmd in cmdArray:
            # Split by '#' to parse command and parameters
            data = oneCmd.split("#")
            # data = ['CMD_MOVE_FORWARD', '50', ...]
```

### 3. **Server Side - Command Routing** (Server.py lines 183-225)

```python
# Immediate execution commands (direct action)
if cmd.CMD_BUZZER in data:
    self.buzzer.run(data[1])           # data = ['CMD_BUZZER', 'on']

elif cmd.CMD_LED in data:
    thread_led = threading.Thread(
        target=self.led.light, args=(data,)
    )
    thread_led.start()

elif cmd.CMD_HEAD in data:
    self.servo.setServoAngle(15, int(data[1]))

elif cmd.CMD_SONIC in data:
    distance = self.sonic.getDistance()
    command = cmd.CMD_SONIC + '#' + str(distance) + "\n"
    self.send_data(self.connection1, command)

# Motion commands (queued in control.order)
else:
    self.control.order = data
    self.control.timeout = time.time()
```

### 4. **Control Execution** (Control.py lines 139-230)

The Control class runs a background thread that continuously checks for queued commands:

```python
def Thread_condition(self):
    while True:
        if self.order[0] != '':  # Command waiting
            if self.order[0] == cmd.CMD_MOVE_STOP:
                self.stop()
                
            elif self.order[0] == cmd.CMD_MOVE_FORWARD:
                self.speed = int(self.order[1])  # Extract speed param
                self.forWard()
                
            elif self.order[0] == cmd.CMD_MOVE_BACKWARD:
                self.speed = int(self.order[1])
                self.backWard()
                
            elif self.order[0] == cmd.CMD_HEIGHT:
                self.upAndDown(int(self.order[1]))
                
            elif self.order[0] == cmd.CMD_CALIBRATION:
                if self.order[1] == "one":
                    self.calibration_point[0][0] = int(self.order[2])
                    self.calibration_point[0][1] = int(self.order[3])
                    self.calibration_point[0][2] = int(self.order[4])
                    self.calibration()
                    self.run()
```

## Command List with Parameters

| Command | Parameters | Example |
|---------|-----------|---------|
| CMD_MOVE_FORWARD | speed | `CMD_MOVE_FORWARD#50` |
| CMD_MOVE_BACKWARD | speed | `CMD_MOVE_BACKWARD#50` |
| CMD_MOVE_STOP | - | `CMD_MOVE_STOP#0` |
| CMD_MOVE_LEFT | speed | `CMD_MOVE_LEFT#50` |
| CMD_MOVE_RIGHT | speed | `CMD_MOVE_RIGHT#50` |
| CMD_TURN_LEFT | speed | `CMD_TURN_LEFT#50` |
| CMD_TURN_RIGHT | speed | `CMD_TURN_RIGHT#50` |
| CMD_HEAD | angle | `CMD_HEAD#90` |
| CMD_HEIGHT | angle | `CMD_HEIGHT#10` |
| CMD_HORIZON | angle | `CMD_HORIZON#5` |
| CMD_ATTITUDE | pitch,yaw,roll | `CMD_ATTITUDE#5#10#3` |
| CMD_BUZZER | type | `CMD_BUZZER#on` |
| CMD_LED | led_data | `CMD_LED#...` |
| CMD_LED_MOD | led_mode | `CMD_LED_MOD#...` |
| CMD_CALIBRATION | leg,x,y,z | `CMD_CALIBRATION#one#0#99#10` |
| CMD_RELAX | flag | `CMD_RELAX#1` |
| CMD_SONIC | - | `CMD_SONIC#0` |
| CMD_POWER | - | `CMD_POWER#0` |
| CMD_WORKING_TIME | - | `CMD_WORKING_TIME#0` |
| CMD_BALANCE | mode | `CMD_BALANCE#1` |

## Key Points

1. **Two TCP Connections**: Port 8001 (video stream) and Port 5001 (commands)
2. **String Protocol**: Commands are UTF-8 encoded strings with format `CMD#param1#param2\n`
3. **Two Execution Paths**:
   - **Immediate**: LED, Buzzer, Head, Sonic, Power, Working Time
   - **Queued**: Movement commands processed by Control thread
4. **Threading**: Heavy operations run in separate threads to prevent blocking
5. **Response Commands**: Server sends back responses for sensor queries (SONIC, POWER, WORKING_TIME)
