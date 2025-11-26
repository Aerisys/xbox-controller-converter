import pygame
import main

def remap_vertical(value):
    mapped = int((1 - value) * 2047.5)
    return max(0, min(4095, mapped))

# --- Configuration Pygame GUI ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREY = (50, 50, 50)
LIGHT_GREY = (150, 150, 150)

def draw_text(screen, text, x, y, size=20, color=WHITE, font_name="Arial"):
    """Fonction utilitaire pour dessiner du texte à l'écran."""
    try:
        font = pygame.font.SysFont(font_name, size)
    except:
        font = pygame.font.Font(None, size)
        
    text_surface = font.render(text, True, color)
    # Centrer le texte horizontalement si x est près du centre (pour le titre principal)
    # Sinon, on utilise l'alignement à gauche pour les coordonnées base_x
    if x > SCREEN_WIDTH / 4 and size > 20:
        text_rect = text_surface.get_rect(center=(x, y))
        screen.blit(text_surface, text_rect)
    else:
        screen.blit(text_surface, (x, y))

def draw_controller_state(screen, snapshot, selected_port, space_was_pressed):
    """Dessine l'état de la manette sur l'écran Pygame."""
    screen.fill(GREY) # Arrière-plan

    # Position de base
    base_x = 50
    y_start = 50
    font_size = 18
    stick_area_size = 100
    stick_radius = 45
    
    # --- 1. Titre et Statut (Déplacé en haut à gauche) ---
    draw_text(screen, "État de la Manette XInput (Pygame / Série)", base_x, 20, 24, WHITE, font_name="consolas")
    
    # --- 2. Gâchettes (Triggers) ---
    trigger_y = y_start + 30 # Décalage pour laisser plus d'espace
    draw_text(screen, "Gâchettes (0.0 - 1.0):", base_x, trigger_y, font_size, WHITE)
    
    # Gâchette Gauche (LT)
    lt_height = int(snapshot['LeftTrigger'] * 100)
    pygame.draw.rect(screen, LIGHT_GREY, (base_x + 10, trigger_y + 40, 20, 100))
    pygame.draw.rect(screen, BLUE, (base_x + 10, trigger_y + 40 + (100 - lt_height), 20, lt_height))
    draw_text(screen, f"LT: {snapshot['LeftTrigger']}", base_x, trigger_y + 160, font_size, WHITE) # Espacé
    draw_text(screen, f"LB: {'ON' if snapshot['LB'] else 'OFF'}", base_x - 10, trigger_y+180, font_size, GREEN if snapshot['LB'] else WHITE)

    # Gâchette Droite (RT)
    rt_height = int(snapshot['RightTrigger'] * 100)
    pygame.draw.rect(screen, LIGHT_GREY, (base_x + 70, trigger_y + 40, 20, 100))
    pygame.draw.rect(screen, RED, (base_x + 70, trigger_y + 40 + (100 - rt_height), 20, rt_height))
    draw_text(screen, f"RT: {snapshot['RightTrigger']}", base_x + 60, trigger_y + 160, font_size, WHITE) # Espacé
    draw_text(screen, f"RB: {'ON' if snapshot['RB'] else 'OFF'}", base_x + 60, trigger_y+180, font_size, GREEN if snapshot['RB'] else WHITE)

    # --- 3. Sticks Analogiques ---
    # Démarre plus bas pour le décalage des gâchettes
    stick_x = base_x + 150
    stick_y = y_start + 30
    
    # Stick Gauche (LS)
    draw_text(screen, "Stick Gauche (-1.0 à 1.0) :", stick_x, stick_y, font_size, WHITE)
    pygame.draw.circle(screen, BLACK, (stick_x + stick_area_size//2, stick_y + stick_area_size//2 + 25), stick_radius + 5, 2)
    # Position du stick (normalisée)
    ls_pos_x = stick_x + stick_area_size // 2 + int(snapshot['LeftStickX'] * stick_radius)
    ls_pos_y = stick_y + stick_area_size // 2 + 25 - int(snapshot['LeftStickY'] * stick_radius) # Le Y est inversé sur l'écran
    pygame.draw.circle(screen, BLUE, (ls_pos_x, ls_pos_y), 10)

    mapped_LX = remap_vertical(snapshot['LeftStickX'])
    mapped_LY = remap_vertical(snapshot['LeftStickY'])
    draw_text(screen, f"X: {snapshot['LeftStickX']:.2f} ({mapped_LX}) / "f"Y: {snapshot['LeftStickY']:.2f} ({mapped_LY})",stick_x,stick_y + 150,font_size,WHITE)    
    draw_text(screen, f"LThumb: {'ON' if snapshot['LThumb'] else 'OFF'}", stick_x, stick_y + 170, font_size, BLUE if snapshot['LThumb'] else WHITE)
    

    # Stick Droit (RS)
    stick_x += 200
    draw_text(screen, "Stick Droit (-1.0 à 1.0) :", stick_x, stick_y, font_size, WHITE)
    pygame.draw.circle(screen, BLACK, (stick_x + stick_area_size//2, stick_y + stick_area_size//2 + 25), stick_radius + 5, 2)
    rs_pos_x = stick_x + stick_area_size // 2 + int(snapshot['RightStickX'] * stick_radius)
    rs_pos_y = stick_y + stick_area_size // 2 + 25 - int(snapshot['RightStickY'] * stick_radius) 
    pygame.draw.circle(screen, RED, (rs_pos_x, rs_pos_y), 10)
    
    mapped_LX = remap_vertical(snapshot['RightStickX'])
    mapped_LY = remap_vertical(snapshot['RightStickY'])

    draw_text(screen, f"X: {snapshot['RightStickX']:.2f} ({mapped_LX}) / "f"Y: {snapshot['RightStickY']:.2f} ({mapped_LY})",stick_x,stick_y + 150,font_size,WHITE)    
    draw_text(screen, f"RThumb: {'ON' if snapshot['RThumb'] else 'OFF'}", stick_x, stick_y + 170, font_size, RED if snapshot['RThumb'] else WHITE)

    # --- 4. Boutons de Façade (A, B, X, Y) ---
    btn_x = 350
    btn_y = 350    
    # Fonction pour dessiner un bouton
    def draw_button(name, value, center_x, center_y, color):
        current_color = color if value else LIGHT_GREY
        text_color = BLACK
        
        # Le bouton "Start" et "Back" seront affichés avec le même style
        if name in ("Back", "Start"):
             current_color = WHITE if value else LIGHT_GREY
             
        pygame.draw.circle(screen, current_color, (center_x, center_y), 15)
        draw_text(screen, name, center_x, center_y - 8, 16, text_color)
    
    draw_button("Y", snapshot['Y'], btn_x + 50, btn_y, YELLOW)
    draw_button("B", snapshot['B'], btn_x + 80, btn_y + 30, RED)
    draw_button("A", snapshot['A'], btn_x + 50, btn_y + 60, GREEN)
    draw_button("X", snapshot['X'], btn_x + 20, btn_y + 30, BLUE)

    # --- 5. D-Pad (Flèches) ---
    dpad_x = 50
    dpad_y = btn_y    
    def draw_dpad_button(name, value, center_x, center_y):
        current_color = WHITE if value else LIGHT_GREY
        pygame.draw.rect(screen, current_color, (center_x - 10, center_y - 10, 20, 20))
        draw_text(screen, name, center_x, center_y - 8, 14, BLACK)

    draw_dpad_button("H", snapshot['DPadUp'], dpad_x + 30, dpad_y)
    draw_dpad_button("B", snapshot['DPadDown'], dpad_x + 30, dpad_y + 60)
    draw_dpad_button("G", snapshot['DPadLeft'], dpad_x, dpad_y + 30)
    draw_dpad_button("D", snapshot['DPadRight'], dpad_x + 60, dpad_y + 30)

    # --- 6. Boutons Centraux (Back et Start) ---
    center_btn_x = 200
    center_btn_y = dpad_y
    draw_text(screen, "Boutons Centraux:", center_btn_x, center_btn_y, font_size, WHITE)
    draw_button("Back", snapshot['Back'], center_btn_x + 10, center_btn_y+50, WHITE)
    draw_button("Start", snapshot['Start'], center_btn_x + 90, center_btn_y+50, WHITE)
    
    draw_text(
        screen,
        f"space : {'Press' if space_was_pressed else 'Not Press'}",
        base_x,
        500,
        font_size,
        GREEN if space_was_pressed else WHITE
    )

    # --- 8. Informations Série/FPS ---
    draw_text(screen, f"Port Série: {selected_port} @ {main.BAUD_RATE}", base_x, 530, font_size, WHITE)


    pygame.display.flip()