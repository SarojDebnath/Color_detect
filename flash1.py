import serial
import time
import random
from serial.tools import list_ports

def find_com_port():
    ports = list_ports.comports()
    for port in ports:
        if 'COM13' in port.device:
            return port.device
    return None

def send_commands(commands):
    try:
        port = find_com_port()
        if not port:
            raise Exception("COM13 not found")

        # Open serial connection
        with serial.Serial(port, 115200, timeout=1) as ser:
            # Verify port is open
            if not ser.is_open:
                ser.open()
            
            # Initial delay for device to stabilize
            time.sleep(1)
            
            # Send initial sequence
            for command in commands:
                ser.write(command.encode())
                response = ser.readline()
                print(f"Sent: {command.strip()}, Response: {response}")
                time.sleep(1)
            
            # Random sequence
            for i in range(22,70):
                #j = random.randint(0,1)
                cmd = f"pts.sh 310 {i} 0 1\n"
                ser.write(cmd.encode())
                response = ser.readline()
                print(f"Sent: {cmd.strip()}, Response: {response}")
                time.sleep(0.25)
            
            ser.write("pts.sh 310  0  0  0\n".encode())
            response = ser.readline()
            # Random sequence
            for i in range(22,70):
                #j = random.randint(0,1)
                cmd = f"pts.sh 310 {i} 0 2\n"
                ser.write(cmd.encode())
                response = ser.readline()
                print(f"Sent: {cmd.strip()}, Response: {response}")
                time.sleep(0.25)
            for i in range(4,22):
                #j = random.randint(0,1)
                cmd = f"pts.sh 310 {i} 0 9\n"
                ser.write(cmd.encode())
                response = ser.readline()
                print(f"Sent: {cmd.strip()}, Response: {response}")
                time.sleep(0.25)

    except serial.SerialException as e:
        print(f"Serial Error: {e}")
    except Exception as e:
        print(f"Error: {e}")


commands = [

    "pts.sh 310  0  0  1\n",
    "pts.sh 310  0  0  0\n",
    "pts.sh 310  0  0  2\n",
    "pts.sh 310  0  0  0\n",
    "pts.sh 310  0  0  9\n",
    "pts.sh 310  0  0  0\n"
]

for l in range(1, 10):
    send_commands(commands)