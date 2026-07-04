import pygame
from time import sleep
from models import engine, vehicle_state, engine_lock, vehicle_state_lock

def show_data():
    pygame.init()
    screen = pygame.display.set_mode((800, 480))
    font = pygame.font.Font(None, 50)
    clock = pygame.time.Clock()
    running = True
    back_color = (0, 0, 120)
    text_color = (255, 255, 255)

    while running: 
        with engine_lock: 
            turbo = engine.turbo_pressure
            rpm = engine.rpm
            oil = engine.oil_temp
            water = engine.water_temperature
            transmission = engine.transmission_temperature
            fuel = engine.fuel_consumption

        with vehicle_state_lock: 
            speed = vehicle_state.speed
            mode = vehicle_state.drive_mode
            voltage = vehicle_state.battery_voltage
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False 
        clock.tick(30)
        screen.fill(back_color)
        text = font.render(f"RPM: {rpm:.0f}", True, text_color)
        screen.blit(text, (100, 100))
        pygame.display.flip()
        sleep(0.5)