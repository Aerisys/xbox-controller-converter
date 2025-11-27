from dataclasses import asdict
import pygame
import serial
import json
import time
import sys
import threading
import os

os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

# Importations spécifiques à votre projet
import controller_to_esp
from select_serial_port import select_serial_port
import view

BAUD_RATE = 115200
DELAY_MS = 10 # 50 ms = 20 FPS (Taux de rafraîchissement)

COLOR_GREEN = '\033[92m'  # Vert clair pour les logs ESP32
COLOR_CYAN = '\033[96m'   # Cyan pour les envois PC
COLOR_RED = '\033[91m'    # Rouge pour les erreurs
COLOR_END = '\033[0m'     # Code pour réinitialiser la couleur

# --- NOUVELLES VARIABLES GLOBALES POUR SYNCHRONISATION ---
# Dictionnaire partagé pour l'état de la manette
controller_snapshot = None 
# Verrou pour protéger l'accès au dictionnaire partagé
snapshot_lock = threading.Lock() 
# Indicateur pour le thread Pygame et le thread principal
running_pygame = True

space_was_pressed = False

serial_port = ""

timestamp = time.strftime("%Y-%m-%d_%H-%M-%S-") + f"{int(time.time() * 1000) % 1000:03d}"
LOG_FILE_PATH = f"mpu_data_log_{timestamp}.csv"

# --- NOUVELLE CLASSE DE THREAD POUR LA LECTURE SÉRIE (CONSOLE ESP32) ---
class SerialReadThread(threading.Thread):
    """Lit les données entrantes du port série (la console de l'ESP32) et les affiche."""
    def __init__(self, ser_connection):
        super().__init__()
        self.ser = ser_connection
        self.running = True
        # Ouverture du log ici pour le thread
        self.log_file = open(LOG_FILE_PATH, "a")
        if os.stat(LOG_FILE_PATH).st_size == 0:
            self.log_file.write("timestamp,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,mag_x,mag_y,mag_z,roll,pitch,yaw\n")

    def run(self):
        print("\n--- Démarrage du Thread de Lecture Série (Console ESP32) ---")
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    while self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"{COLOR_GREEN}[ESP32 LOG {time.strftime('%H:%M:%S')}] {line}{COLOR_END}")

                            # --- ÉCRITURE DANS LE FICHIER LOG CSV ---
                            if line.startswith("MPU_DATA"):
                                parts = line.split(",")
                                if len(parts) == 13:  # 12 floats + "MPU_DATA"
                                    timestamp = time.time()
                                    if len(parts) == 13:  # 12 floats + "MPU_DATA"
                                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(time.time() * 1000) % 1000:03d}"
                                        self.log_file.write(f"{timestamp},{','.join(parts[1:])}\n")
                                        self.log_file.flush()

                time.sleep(0.1)

            except Exception as e:
                if self.running:
                    print(f"❌ Erreur de lecture série. Arrêt du thread: {e}", file=sys.stderr)
                break
        print("Thread de Lecture Série terminé.")
        self.log_file.close()

    def stop(self):
        """Signale au thread de s'arrêter proprement."""
        self.running = False


# --- CLASSE DE THREAD POUR L'AFFICHAGE PYGAME ---
class PygameViewThread(threading.Thread):
    def __init__(self, serial_port_open):
        super().__init__()
        self.serial_port_open = serial_port_open

    def run(self):
        global controller_snapshot, running_pygame, serial_port, space_was_pressed
        
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
                view.draw_controller_state(screen, local_snapshot, serial_port, space_was_pressed)
                
            # Limiter le taux de rafraîchissement du thread Pygame à 30 FPS par exemple
            clock.tick(30) # Limite à 30 images par seconde max
            
        pygame.quit()
        print("Thread Pygame terminé.")

# --- THREAD PRINCIPAL (Lecture Manette et Envoi Série) ---
def main():
    global controller_snapshot, running_pygame, serial_port, space_was_pressed

    # --- 0. Sélection du Port Série ---
    selected_port = select_serial_port()
    if selected_port is None:
        sys.exit(1)
    serial_port = selected_port
    
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
        
    except Exception as e:
        print(f"❌ Erreur d'initialisation de la manette : {e}", file=sys.stderr)
        pygame.quit()
        sys.exit(1)

    # --- 2. Initialisation du Port Série ---
    ser = None
    serial_port_open = False
    try:
        # Initialisation série : Timeout à 0 pour la lecture non bloquante dans le thread dédié
        ser = serial.Serial(selected_port, BAUD_RATE, timeout=0)
        time.sleep(2) # Attendre un peu pour que l'ESP32 redémarre (cycle DTR/RTS)
        print(f"✅ Port série {selected_port} ouvert. Début de la transmission.")
        serial_port_open = True
            
    except serial.SerialException as e:
        print(f"❌ Erreur de port série. Assurez-vous que '{selected_port}' est correct et libre. Détail: {e}", file=sys.stderr)
        pygame.quit()
        sys.exit(1)
        
    # --- 3. Démarrage des Threads ---
    
    # Thread 1 : Affichage Pygame
    pygame_thread = PygameViewThread(serial_port_open)
    pygame_thread.start()
    
    # Thread 2 : Lecture Console ESP32
    serial_read_thread = SerialReadThread(ser)
    serial_read_thread.start() 

    # --- 4. Boucle Principale (Lecture Manette et Envoi Série) ---
    print("\n--- Lecture Manette et Envoi Série (Ctrl+C ou fermer fenêtre pour arrêter) ---")
    running_main = True

    # Ouvrir le fichier log
    log_file = open(LOG_FILE_PATH, "a")
    # Écrire l'en-tête CSV si le fichier est vide
    if os.stat(LOG_FILE_PATH).st_size == 0:
        log_file.write("timestamp,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,mag_x,mag_y,mag_z,roll,pitch,yaw\n")

    
    try:
        while running_main:
            # Vérifiez si le thread d'affichage a demandé l'arrêt
            if not running_pygame:
                running_main = False
                break
                
            # Lire l'état de la manette
            snapshot, packet = controller_to_esp.map_xbox_controller(joystick)
            
            if snapshot:
                # Mettre à jour le snapshot partagé (avec verrou)
                with snapshot_lock:
                    controller_snapshot = snapshot
                
                try:
                    if ser and ser.is_open:
                        # ENVOI des données JSON
                        ser.write(packet)
                    
                    # Affichage pour le débogage de l'envoi
                    # print(f"[PC TX {time.strftime('%H:%M:%S')}] Envoi ({len(json_data)} octets) : {json_data}")

                except serial.SerialTimeoutException:
                    print("Timeout d'envoi série.", file=sys.stderr)
                except Exception as e:
                    print(f"Erreur d'écriture série: {e}", file=sys.stderr)
            keys = pygame.key.get_pressed()
            space_pressed = keys[pygame.K_SPACE]

            # Détection front montant / descendant
            if space_pressed != space_was_pressed:
                try:
                    snapshotTmp = controller_to_esp.XboxControllerData(
                        Back=1 if space_pressed else 0
                    )
                    packetSpace = snapshotTmp.to_controller_packet()
                    snapshotSpace = asdict(snapshotTmp)
                    if snapshotSpace:
                        try:
                            if ser and ser.is_open:
                                # ENVOI des données JSON
                                ser.write(packetSpace)
                            
                            # Affichage pour le débogage de l'envoi
                            # print(f"[PC TX {time.strftime('%H:%M:%S')}] Envoi ({len(json_data)} octets) : {json_data}")

                        except serial.SerialTimeoutException:
                            print("Timeout d'envoi série.", file=sys.stderr)
                        except Exception as e:
                            print(f"Erreur d'écriture série: {e}", file=sys.stderr)
                except:
                    pass

            # Mise à jour
            space_was_pressed = space_pressed
            time.sleep(DELAY_MS / 1000.0) # Pause pour contrôler la fréquence

    except KeyboardInterrupt:
        print("\nArrêt par l'utilisateur (Ctrl+C).")
    finally:
        # 5. Nettoyage
        
        # Signaler aux threads de s'arrêter
        running_pygame = False 
        
        # Arrêter le thread de lecture série
        serial_read_thread.stop() 
        
        # Attendre la fin des threads
        pygame_thread.join() 
        serial_read_thread.join()
        
        # Assurer la fermeture propre du port série
        if ser and ser.is_open:
            ser.close()
            print("Port série fermé.")
            
        # Fermer l'initialisation Pygame restante dans le thread principal
        pygame.quit()
        print("Programme principal terminé.")

        if log_file:
            log_file.close()
            print(f"Fichier log fermé : {LOG_FILE_PATH}")


if __name__ == "__main__":
    main()