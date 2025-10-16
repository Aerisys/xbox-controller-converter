import pygame
import serial
import json
import time

# Initialisation Pygame et manette
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise Exception("Aucune manette détectée !")

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Manette détectée : {joystick.get_name()}")

# Ouvre le port série de l'ESP32 (adapter le COMx)
ser = serial.Serial('COM5', 115200, timeout=1)
time.sleep(2)  # Laisser le temps à l’ESP32 de se lancer

while True:
    pygame.event.pump()

    # Récupère les valeurs utiles (exemple : 2 axes, 2 triggers, 4 boutons)
    axes = [round(joystick.get_axis(i), 2) for i in range(4)]  # sticks
    buttons = [joystick.get_button(i) for i in range(4)]  # boutons A/B/X/Y

    # Prépare un dictionnaire
    data = {
        "axes": axes,
        "buttons": buttons
    }

    # Envoie sous forme JSON
    ser.write((json.dumps(data) + "\n").encode('utf-8'))

    print("Envoi :", data)
    time.sleep(0.05)  # ~20 FPS
