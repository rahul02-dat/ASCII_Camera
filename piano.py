import sys
import numpy as np
import pygame

# 1. Initialize Audio Mixer and Pygame
SAMPLE_RATE = 44100
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=256)
pygame.init()
pygame.font.init()

# Setup GUI window dimensions and typography
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 350
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Procedural Piano - Visualizer")

# Use standard system font
FONT_LARGE = pygame.font.SysFont("Arial", 48, bold=True)
FONT_SMALL = pygame.font.SysFont("Arial", 18)

# Color Definitions (RGB)
COLOR_BG = (20, 24, 30)        # Dark slate
COLOR_TEXT = (230, 235, 240)    # Off-white
COLOR_NOTE = (0, 200, 150)      # Mint green accent
COLOR_MUTED = (100, 110, 120)   # Gray for instructions

def generate_piano_sound(frequency, duration=1.5):
    """Generates a synthesized piano note using an exponential decay envelope."""
    total_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, total_samples, False)
    
    # Fundamental tone + overtones
    wave = np.sin(2 * np.pi * frequency * t)
    wave += 0.5 * np.sin(2 * np.pi * (2 * frequency) * t)
    wave += 0.25 * np.sin(2 * np.pi * (3 * frequency) * t)
    
    # Exponential decay envelope
    envelope = np.exp(-3.5 * t)
    audio_data = wave * envelope
    normalized_wave = (audio_data / np.max(np.abs(audio_data))) * 0.6
    
    int_audio = (normalized_wave * 32767).astype(np.int16)
    return pygame.mixer.Sound(buffer=int_audio)

# 2. Key Mapping with Metadata for the Visualizer
# Format: pygame_key: (Frequency, "Note Name", "Key Label")
NOTE_DETAILS = {
    pygame.K_a: (261.63, "C4", "A"),
    pygame.K_w: (277.18, "C#4", "W"),
    pygame.K_s: (293.66, "D4", "S"),
    pygame.K_e: (311.13, "D#4", "E"),
    pygame.K_d: (329.63, "E4", "D"),
    pygame.K_f: (349.23, "F4", "F"),
    pygame.K_t: (369.99, "F#4", "T"),
    pygame.K_g: (392.00, "G4", "G"),
    pygame.K_y: (415.30, "G#4", "Y"),
    pygame.K_h: (440.00, "A4", "H"),
    pygame.K_u: (466.16, "A#4", "U"),
    pygame.K_j: (493.88, "B4", "J"),
    pygame.K_k: (523.25, "C5", "K"),
}

print("Pre-rendering synthesized audio patches...")
PIANO_PATCH = {key: generate_piano_sound(data[0]) for key, data in NOTE_DETAILS.items()}
print("System ready.")

# 3. Execution Loop variables
running = True
active_channels = {}
current_note_text = "None"
current_key_text = "-"

while running:
    # Handle Input Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
                
            elif event.key in PIANO_PATCH and event.key not in active_channels:
                # Play audio
                channel = PIANO_PATCH[event.key].play()
                active_channels[event.key] = channel
                
                # Update visual text values based on the pressed key
                current_note_text = NOTE_DETAILS[event.key][1]
                current_key_text = NOTE_DETAILS[event.key][2]
                
        elif event.type == pygame.KEYUP:
            if event.key in active_channels:
                if active_channels[event.key]:
                    active_channels[event.key].fadeout(150)
                del active_channels[event.key]
            
            # Reset UI text if no keys are currently held down
            if not active_channels:
                current_note_text = "None"
                current_key_text = "-"

    # 4. Drawing the Interface
    screen.fill(COLOR_BG)
    
    # Render static instruction labels
    instr_surface = FONT_SMALL.render("Play melody using QWERTY home row. Press ESC to quit.", True, COLOR_MUTED)
    screen.blit(instr_surface, (20, 20))
    
    key_lbl_surface = FONT_SMALL.render("Keyboard Key Pressed:", True, COLOR_MUTED)
    screen.blit(key_lbl_surface, (50, 120))
    
    note_lbl_surface = FONT_SMALL.render("Musical Note Playing:", True, COLOR_MUTED)
    screen.blit(note_lbl_surface, (280, 120))
    
    # Render dynamic state text (the values that change when you type)
    key_val_surface = FONT_LARGE.render(current_key_text, True, COLOR_TEXT)
    # Centering logic adjustment for position
    screen.blit(key_val_surface, (110, 160))
    
    note_val_surface = FONT_LARGE.render(current_note_text, True, COLOR_NOTE)
    screen.blit(note_val_surface, (280, 160))
    
    # Refresh display
    pygame.display.flip()

pygame.quit()
sys.exit()