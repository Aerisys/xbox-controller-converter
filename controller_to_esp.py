import pygame
import sys
import struct
from dataclasses import dataclass, asdict, field

import platform 
system = platform.system()

mappings = {
    "Windows": {"ls_x":0, "ls_y":1, "rs_x":2, "rs_y":3, "lt":4, "rt":5},
    "Linux":   {"ls_x":0, "ls_y":1, "rs_x":3, "rs_y":4, "lt":2, "rt":5},
    "Default": {"ls_x":0, "ls_y":1, "rs_x":2, "rs_y":3, "lt":4, "rt":5}
}

mapping = mappings.get(system, mappings["Default"])

@dataclass
class XboxControllerData:
    """
    Classe représentant l'état complet et brut de la manette (Pygame).
    """
    # Axes analogiques (-1.0 à 1.0)
    LeftStickX: float = 0.0
    LeftStickY: float = 0.0
    RightStickX: float = 0.0
    RightStickY: float = 0.0
    
    # Gâchettes (0.0 à 1.0)
    LeftTrigger: float = 0.0
    RightTrigger: float = 0.0
    
    # Boutons (0 ou 1)
    A: int = 0
    B: int = 0
    X: int = 0
    Y: int = 0
    LB: int = 0
    RB: int = 0
    Back: int = 0
    Start: int = 0
    LThumb: int = 0
    RThumb: int = 0
    
    # D-Pad (0 ou 1)
    DPadUp: int = 0
    DPadDown: int = 0
    DPadLeft: int = 0
    DPadRight: int = 0

    def to_controller_packet(self) -> bytes:
        # floats
        RightStickY = remap_vertical(self.RightStickY)
        RightStickX = remap_vertical(self.RightStickX)
        LeftStickY = remap_vertical(self.LeftStickY)
        LeftStickX = remap_vertical(self.LeftStickX)

        motorState = 1 if self.Back else 0
        motorArming = 1 if self.Start else 0

        print(f"Joystick gauche : X={LeftStickX}, Y={LeftStickY} | Joystick droit : X={RightStickX}, Y={RightStickY} | MotorState={motorState} | MotorArming={motorArming}")

        payload = struct.pack("<ffffBB",
            -RightStickY,
            -RightStickX,
            -LeftStickY,
            -LeftStickX,
            motorState,
            motorArming
        )

        header = b"\xAA\x55"
        length = bytes([len(payload)])

        checksum = bytes([sum(payload) & 0xFF])

        return header + length + payload + checksum

def remap_vertical(x):
    mapped = int((1 - x) * 2047.5)
    return max(0, min(4095, mapped))


def map_xbox_controller(joystick):
    """
    Lit l'état, crée un XboxControllerData, le convertit en ControllerRequestDTO
    et retourne le dictionnaire JSON final.
    """
    global packet_counter
    
    try:
        pygame.event.pump()

        # --- 1. LECTURE BRUTE ---
        ls_x = round(joystick.get_axis(mapping["ls_x"]), 2)
        ls_y = round(joystick.get_axis(mapping["ls_y"]) * -1, 2) 
        rs_x = round(joystick.get_axis(mapping["rs_x"]), 2)
        rs_y = round(joystick.get_axis(mapping["rs_y"]) * -1, 2)

        num_axes = joystick.get_numaxes()
        lt_raw = joystick.get_axis(mapping["lt"]) if num_axes > mapping["lt"] else -1.0
        rt_raw = joystick.get_axis(mapping["rt"]) if num_axes > mapping["rt"] else -1.0
        lt = round(max(0.0, (lt_raw + 1) / 2), 2)
        rt = round(max(0.0, (rt_raw + 1) / 2), 2)

        hat = joystick.get_hat(0)

        # --- 2. REMPLISSAGE DONNÉES BRUTES ---
        xbox_data = XboxControllerData(
            LeftStickX=ls_x, LeftStickY=ls_y,
            RightStickX=rs_x, RightStickY=rs_y,
            LeftTrigger=lt, RightTrigger=rt,
            A=joystick.get_button(0), B=joystick.get_button(1),
            X=joystick.get_button(2), Y=joystick.get_button(3),
            LB=joystick.get_button(4), RB=joystick.get_button(5),
            Back=joystick.get_button(6), Start=joystick.get_button(7),
            LThumb=joystick.get_button(8), RThumb=joystick.get_button(9),
            DPadUp=1 if hat[1] == 1 else 0,
            DPadDown=1 if hat[1] == -1 else 0,
            DPadLeft=1 if hat[0] == -1 else 0,
            DPadRight=1 if hat[0] == 1 else 0
        )
        
        packet = xbox_data.to_controller_packet()

        # Retourne le dictionnaire structuré comme le C++ l'attend
        return asdict(xbox_data), packet

    except pygame.error as e:
        print(f"Erreur de lecture de la manette: {e}", file=sys.stderr)
        return None