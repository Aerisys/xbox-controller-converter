import pygame
import sys

import serial

def map_xbox_controller(joystick):
    """
    Lit l'état complet d'une manette Xbox et retourne un dictionnaire contenant
    tous les sticks, gâchettes et boutons, normalisés pour l'ESP32.
    """
    try:
        # Assurez-vous que les événements Pygame sont mis à jour
        pygame.event.pump()

        # --- 1. AXES (Sticks) ---
        ls_x = round(joystick.get_axis(0), 2)
        ls_y = round(joystick.get_axis(1) * -1, 2) 
        
        rs_x = round(joystick.get_axis(2), 2)
        rs_y = round(joystick.get_axis(3) * -1, 2)

        # --- 2. GÂCHETTES (Triggers) ---
        lt_raw = joystick.get_axis(4) if joystick.get_numaxes() > 2 else -1.0
        rt_raw = joystick.get_axis(5) if joystick.get_numaxes() > 5 else -1.0
        
        lt = round(max(0.0, (lt_raw + 1) / 2), 2)
        rt = round(max(0.0, (rt_raw + 1) / 2), 2)


        # --- 3. BOUTONS et D-PAD ---
        buttons = {
            # Face Buttons
            "A": joystick.get_button(0), "B": joystick.get_button(1),
            "X": joystick.get_button(2), "Y": joystick.get_button(3),
            # Bumpers et Clics Sticks
            "LB": joystick.get_button(4), "RB": joystick.get_button(5),
            "Back": joystick.get_button(6), "Start": joystick.get_button(7),
            "LThumb": joystick.get_button(8), "RThumb": joystick.get_button(9),
        }
        
        hat = joystick.get_hat(0)
        
        dpad = {
            "DPadUp": 1 if hat[1] == 1 else 0,
            "DPadDown": 1 if hat[1] == -1 else 0,
            "DPadLeft": 1 if hat[0] == -1 else 0,
            "DPadRight": 1 if hat[0] == 1 else 0,
        }

        # --- 4. Construction du Dictionnaire de données final ---
        snapshot = {
            # Axes analogiques normalisés (-1.0 à 1.0)
            "LeftStickX": ls_x, "LeftStickY": ls_y, 
            "RightStickX": rs_x, "RightStickY": rs_y,
            # Gâchettes normalisées (0.0 à 1.0)
            "LeftTrigger": lt, "RightTrigger": rt,
            # Boutons (0 ou 1)
            **buttons,
            **dpad
        }
        
        return snapshot

    except pygame.error as e:
        print(f"Erreur de lecture de la manette: {e}", file=sys.stderr)
        return None


