import pygame
import serial
import json
import time
import sys
import threading

import controller_to_esp
from select_serial_port import select_serial_port
import view

BAUD_RATE = 115200
DELAY_MS = 50 # 50 ms = 20 FPS (Taux de rafraîchissement)

# --- NOUVELLES VARIABLES GLOBALES POUR SYNCHRONISATION ---
# Dictionnaire partagé pour l'état de la manette
controller_snapshot = None 
# Verrou pour protéger l'accès au dictionnaire partagé
snapshot_lock = threading.Lock() 
# Indicateur pour le thread Pygame
running_pygame = True

serial_port = ""

# --- NOUVELLE CLASSE DE THREAD POUR L'AFFICHAGE ---
class PygameViewThread(threading.Thread):
    def __init__(self, serial_port_open):
        super().__init__()
        self.serial_port_open = serial_port_open

    def run(self):
        global controller_snapshot, running_pygame, serial_port
        
        # Initialisation Pygame dans le thread
        pygame.init()
        pygame.joystick.init()
        pygame.font.init()
        
        screen = pygame.display.set_mode((view.SCREEN_WIDTH, view.SCREEN_HEIGHT))
        pygame.display.set_caption("Lecteur Manette XInput pour ESP32 (Thread Affichage)")
        
        clock = pygame.time.Clock() # Utilisé pour contrôler le taux de rafraîchissement (optionnel)
        
        print("\n--- Démarrage du Thread Pygame pour l'affichage ---")

        while running_pygame:
            # Gère les événements de la fenêtre (fermeture)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running_pygame = False
            
            # Affichage graphique
            # N'essayez d'afficher que si un snapshot est disponible
            if controller_snapshot:
                with snapshot_lock:
                    # Crée une copie locale pour l'affichage (éviter un accès prolongé au verrou)
                    local_snapshot = controller_snapshot.copy() 
                
                # --- A. AFFICHAGE GRAPHIQUE ---
                view.draw_controller_state(screen, local_snapshot)
                
            # Limiter le taux de rafraîchissement du thread Pygame à 30 FPS par exemple
            # Cela permet de laguer l'affichage sans ralentir le thread principal
            clock.tick(30) # Limite à 30 images par seconde max
            
        pygame.quit()
        print("Thread Pygame terminé.")
        
# --- ANCIENNE FONCTION MAIN (Maintenant le Thread Principal) ---
def main():
    global controller_snapshot, running_pygame, serial_port

    # --- 0. Sélection du Port Série ---
    selected_port = select_serial_port()
    if selected_port is None:
        sys.exit(1)
    
    # Initialisation Pygame (nécessaire pour la lecture de manette)
    pygame.init()
    pygame.joystick.init()

    # --- 1. Initialisation Manette ---
    try:
        if pygame.joystick.get_count() == 0:
            print("❌ Aucune manette XInput détectée ! Veuillez la connecter.")
            pygame.quit()
            sys.exit(1)

        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"✅ Manette détectée : {joystick.get_name()}")
        
        # --- 2. Initialisation du Port Série (Commenté pour le test) ---
        ser = serial.Serial(selected_port, BAUD_RATE, timeout=0.1)
        ser = None # Simuler l'objet série
        time.sleep(2)  
        print(f"✅ Port série {selected_port} ouvert. Début de la transmission.")
        serial_port_open = True
            
    except serial.SerialException as e:
        print(f"❌ Erreur de port série. Assurez-vous que '{selected_port}' est correct et libre. Détail: {e}", file=sys.stderr)
        pygame.quit()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur d'initialisation : {e}", file=sys.stderr)
        pygame.quit()
        sys.exit(1)

    # --- 3. Démarrage du Thread Pygame ---
    pygame_thread = PygameViewThread(serial_port_open)
    pygame_thread.start()

    # --- 4. Boucle Principale (Lecture Manette et Envoi Série) ---
    print("\n--- Lecture Manette et Envoi Série (Ctrl+C pour arrêter) ---")
    running_main = True
    
    try:
        while running_main:
            # Vérifiez si le thread d'affichage a demandé l'arrêt (fermeture de la fenêtre)
            if not running_pygame:
                running_main = False
                break
                
            # Lire l'état de la manette
            snapshot = controller_to_esp.map_xbox_controller(joystick)
            
            if snapshot:
                # Mettre à jour le snapshot partagé (avec verrou)
                with snapshot_lock:
                    controller_snapshot = snapshot
                
                # --- B. ENVOI SÉRIE (Prioritaire) ---
                json_data = json.dumps(snapshot, separators=(',', ':'))
                
                try:
                    if ser:
                        ser.write((json_data + "\n").encode('utf-8'))
                    # Affichage pour le débogage de la console (peut être retiré)
                    print(f"Envoi ({len(json_data)} octets) : {json_data}")
                    pass

                except serial.SerialTimeoutException:
                    print("Timeout d'envoi série.", file=sys.stderr)
                except Exception as e:
                    print(f"Erreur d'écriture série: {e}", file=sys.stderr)
                
            time.sleep(DELAY_MS / 1000.0) # Pause pour contrôler la fréquence

    except KeyboardInterrupt:
        print("\nArrêt par l'utilisateur (Ctrl+C).")
    finally:
        # 5. Nettoyage
        
        # Signaler au thread Pygame de s'arrêter
        running_pygame = False 
        
        # Attendre la fin du thread Pygame
        pygame_thread.join() 
        
        # Assurer la fermeture propre du port série
        if ser and ser.is_open:
            # ser.close()
            print("Port série fermé.")
            
        # Fermer l'initialisation Pygame restante dans le thread principal
        pygame.quit()
        print("Programme principal terminé.")

if __name__ == "__main__":
    main()