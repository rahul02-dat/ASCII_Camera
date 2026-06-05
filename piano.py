import sys
import numpy as np
import pygame

# 1. Initialize Audio Mixer with optimized buffer for low latency
SAMPLE_RATE = 44100
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=256)
pygame.init()

# Setup a window to capture keyboard input
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Procedural Python Piano")

def generate_piano_sound(frequency, duration=1.5):
    """Generates a synthesized piano note using sine waves and an exponential decay envelope."""
    total_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, total_samples, False)
    
    # Fundamental frequency
    wave = np.sin(2 * np.pi * frequency * t)
    
    # Overtones / Harmonics to enrich the timbre (makes it sound less like a computer beep)
    wave += 0.5 * np.sin(2 * np.pi * (2 * frequency) * t)  # First harmonic
    wave += 0.25 * np.sin(2 * np.pi * (3 * frequency) * t) # Second harmonic
    
    # Volume Envelope: Fast attack, exponential decay to simulate a string strike
    # Formula: Amplitude = exp(-decay_rate * t)
    envelope = np.exp(-3.5 * t)
    
    # Combine wave and envelope, then normalize to peak volume
    audio_data = wave * envelope
    normalized_wave = (audio_data / np.max(np.abs(audio_data))) * 0.6
    
    # Convert to 16-bit signed integers for Pygame Buffer
    int_audio = (normalized_wave * 32767).astype(np.int16)
    return pygame.mixer.Sound(buffer=int_audio)

# 2. Map Keys to Standard Equal Temperament Frequencies (Middle Octave)
# Formula used: f = 440 * 2^((n-69)/12)
NOTE_FREQS = {
    pygame.K_a: 261.63,  # C4
    pygame.K_w: 277.18,  # C#4 / Db4
    pygame.K_s: 293.66,  # D4
    pygame.K_e: 311.13,  # D#4 / Eb4
    pygame.K_d: 329.63,  # E4
    pygame.K_f: 349.23,  # F4
    pygame.K_t: 369.99,  # F#4 / Gb4
    pygame.K_g: 392.00,  # G4
    pygame.K_y: 415.30,  # G#4 / Ab4
    pygame.K_h: 440.00,  # A4 (Standard Tuning)
    pygame.K_u: 466.16,  # A#4 / Bb4
    pygame.K_j: 493.88,  # B4
    pygame.K_k: 523.25,  # C5 (Next Octave Start)
}

print("Generating synthesized instrument notes into memory...")
PIANO_PATCH = {key: generate_piano_sound(freq) for key, freq in NOTE_FREQS.items()}
print("Generation complete. System Ready.")

# 3. Execution Loop
running = True
active_channels = {}

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
                
            elif event.key in PIANO_PATCH and event.key not in active_channels:
                # Play note on an open channel
                channel = PIANO_PATCH[event.key].play()
                active_channels[event.key] = channel
                
        elif event.type == pygame.KEYUP:
            if event.key in active_channels:
                if active_channels[event.key]:
                    # Smoothly fade out the note to mimic lifting off a piano key
                    active_channels[event.key].fadeout(150)
                del active_channels[event.key]

pygame.quit()
sys.exit()