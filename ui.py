import pygame
from time import sleep
from models import engine, vehicle_state, engine_lock, vehicle_state_lock

def show_data():
    pygame.init()
    screen = pygame.display.set_mode((800, 480))
    font = pygame.font.Font(None, 50)
    clock = pygame.time.Clock()
    running = True
    back_color = (92, 93, 87)
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

        chanels = [
            ("Turbo", turbo, None, None), #(label, value, min limit, max limit)
            ("RPM", rpm, None, 5000), 
            ("Oil Temperature", oil, None, 115),
            ("Water Temperature", water, None, 110),
            ("Transmission Temperature", transmission, None, 96),
            ("Fuel Consumption", fuel, None, None), 
            ("Speed", speed, None, None),
            ("Battery Voltage", voltage, 11.8, None)
        ]
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False 
        

        screen.fill(back_color)
    
        y = 50
        for label, value, min_limit, max_limit in chanels:
            danger = (min_limit is not None and value <= min_limit) or (max_limit is not None and value >= max_limit)
            if danger:
                text_color = (255, 0, 0)
            else:
                text_color = (255, 255, 255)
            text = font.render(f"{label}: {value:.1f}", True, text_color)
            screen.blit(text, (100, y))
            y += 50
        
        clock.tick(30)
        pygame.display.flip()
