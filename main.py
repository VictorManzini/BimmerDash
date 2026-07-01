from time import sleep
from models import engine, vehicle_state

while True:
    
    for engine.turbo_pressure in range(0, 19):
        print(f"Pressão de turbina: {engine.read_boost():.2f} psi")
        sleep(0.5)
    
    for engine.turbo_pressure in range(19, -1, -1):
        print(f"Pressão de turbina: {engine.read_boost():.2f} psi")
        sleep(0.5)
