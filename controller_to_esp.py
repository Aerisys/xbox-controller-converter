import pygame
import serial
import json
import time
import sys

import view

# --- Configuration ---
# REMARQUE IMPORTANTE : Changer ce port en fonction de votre OS et du port de l'ESP32.
SERIAL_PORT = 'COM5'  # <-- À CHANGER SELON VOTRE SYSTÈME !
BAUD_RATE = 115200
DELAY_MS = 50  # 50 ms = 20 FPS (Taux de rafraîchissement)



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


def main():
    # --- 1. Initialisation Pygame et Manette ---
    pygame.init()
    pygame.joystick.init()
    pygame.font.init()
    
    # Initialisation de la fenêtre Pygame
    screen = pygame.display.set_mode((view.SCREEN_WIDTH, view.SCREEN_HEIGHT))
    pygame.display.set_caption("Lecteur Manette XInput pour ESP32")


    try:
        if pygame.joystick.get_count() == 0:
            print("❌ Aucune manette XInput détectée ! Veuillez la connecter.")
            pygame.quit()
            sys.exit(1)

        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"✅ Manette détectée : {joystick.get_name()}")
        
        # --- 2. Initialisation du Port Série ---
        #ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)  # Attendre que la connexion série soit stable
        print(f"✅ Port série {SERIAL_PORT} ouvert. Début de la transmission.")
            
    except serial.SerialException as e:
        print(f"❌ Erreur de port série. Assurez-vous que '{SERIAL_PORT}' est correct et libre. Détail: {e}", file=sys.stderr)
        pygame.quit()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur d'initialisation : {e}", file=sys.stderr)
        pygame.quit()
        sys.exit(1)

    # --- 3. Boucle Principale ---
    print("\n--- Envoi des données JSON et Affichage graphique (Ctrl+C pour arrêter) ---")
    running = True
    
    try:
        while running:
            # Gère les événements de la fenêtre (fermeture)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Lire l'état de la manette
            snapshot = map_xbox_controller(joystick)
            
            if snapshot:
                # --- A. AFFICHAGE GRAPHIQUE ---
                view.draw_controller_state(screen, snapshot)
                
                # --- B. ENVOI SÉRIE ---
                json_data = json.dumps(snapshot, separators=(',', ':'))
                
                try:
                    #ser.write((json_data + "\n").encode('utf-8'))
                    print()
                    # Affichage des données envoyées dans la console (pour le débogage)
                    # print(f"Envoi ({len(json_data)} octets) : {json_data}")
                except serial.SerialTimeoutException:
                    print("Timeout d'envoi série.", file=sys.stderr)
                except Exception as e:
                    print(f"Erreur d'écriture série: {e}", file=sys.stderr)
                
            time.sleep(DELAY_MS / 1000.0) # Pause pour contrôler la fréquence

    except KeyboardInterrupt:
        print("\nArrêt par l'utilisateur (Ctrl+C).")
    finally:
        # Assurer la fermeture propre de toutes les ressources
        if 'ser' in locals() and ser.is_open:
            #ser.close()
            print("Port série fermé.")
        pygame.quit()
        print("Pygame terminé.")

if __name__ == "__main__":
    main()