import struct
import serial

# float = 4 bytes
# Vector3 = 3 floats = 12 bytes
# Orientation = 3 floats = 12 bytes
# mpuDTO = 4 * Vector3 = 48 bytes
PACKET_SIZE = 48

ser = serial.Serial("/dev/ttyUSB0", 115200)

while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()

    print(line)
