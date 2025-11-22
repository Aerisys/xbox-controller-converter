import serial
import serial.tools.list_ports


def select_serial_port():
    """Liste les ports série disponibles et demande à l'utilisateur d'en choisir un."""
    
    # 1. Lister les ports
    available_ports = serial.tools.list_ports.comports()
    
    if not available_ports:
        print("❌ Aucun port série COM/tty détecté ! Assurez-vous que l'ESP32 est connecté.")
        return None

    print("\n--- Ports Série Disponibles ---")
    
    # 2. Afficher la liste des ports
    ports_dict = {}
    for i, port in enumerate(available_ports):
        # Pour une meilleure lisibilité, on affiche le nom (device) et la description (desc)
        print(f"  [{i}] : {port.device} ({port.description})")
        ports_dict[i] = port.device
        
    print("---------------------------------")
    
    # 3. Demander le choix à l'utilisateur
    while True:
        try:
            choice = input(f"Veuillez entrer le numéro du port à utiliser (0 à {len(available_ports) - 1}) : ")
            choice_index = int(choice)
            
            if choice_index in ports_dict:
                selected_port = ports_dict[choice_index]
                print(f"✅ Port sélectionné : {selected_port}")
                return selected_port
            else:
                print("Numéro invalide. Veuillez réessayer.")
        except ValueError:
            print("Entrée invalide. Veuillez entrer un nombre.")