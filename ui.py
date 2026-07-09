import pygame
import math
from time import sleep
from gauges import gauge_config, value_to_angle, angle_to_coordinate
from models import engine, vehicle_state, engine_lock, vehicle_state_lock, stop_event

def draw_needle(screen, value, channel, cx, cy, radius):
    config = gauge_config[channel]
    angle = value_to_angle(value, config["min"], config["max"], config["arc_start"], config["arc_end"])
    tip = angle_to_coordinate(angle, cx, cy, radius)
    pygame.draw.line(screen, (255, 0,0), (cx, cy), tip, 4)

def draw_ticks(screen, channel, cx, cy, radius, font_small):
    arc_color = (255, 255, 255)
    config = gauge_config[channel]
    value = config["min"]
    while value <= config["max"]: 
        angle = value_to_angle(value, config["min"], config["max"], config["arc_start"], config["arc_end"])
        p_out = angle_to_coordinate(angle, cx, cy, radius)
        p_in = angle_to_coordinate(angle, cx, cy, radius -15)
        p_label = angle_to_coordinate(angle, cx, cy, radius - 25)
        pygame.draw.line(screen, arc_color, p_in, p_out, 3)
        label = font_small.render(str(int(value)), True, arc_color)
        screen.blit(label, label.get_rect(center=p_label))
        value += config["tick_step"]

def draw_arc_background(screen, channel, cx, cy, radius):
    arc_color = (255, 255, 255)
    config = gauge_config[channel]
    steps = 60
    step_value = (config["max"] - config["min"]) / steps
    for i in range(steps): 
        current_value = config["min"] +i * step_value 
        next_value = config["min"] + (i + 1) * step_value
        current_angle = value_to_angle(current_value, config["min"], config["max"], config["arc_start"], config["arc_end"])
        next_angle = value_to_angle(next_value, config["min"], config["max"], config["arc_start"], config["arc_end"])
        p1 = angle_to_coordinate(current_angle, cx, cy, radius)
        p2 = angle_to_coordinate(next_angle, cx, cy, radius)
        pygame.draw.line(screen, arc_color, p1, p2, 4)
    

def show_data():
    pygame.init()
    screen = pygame.display.set_mode((800, 480))
    font = pygame.font.Font(None, 45)
    font_small = pygame.font.Font(None, 20)
    clock = pygame.time.Clock()
    running = True
    back_color = (92, 93, 87)
    text_color = (255, 255, 255)
    mode_color = (255, 255, 255)

    mode_keys = {
        pygame.K_1: "Comfort", 
        pygame.K_2: "Sport", 
        pygame.K_3: "Sport+", 
        pygame.K_4: "ECO PRO", 
    }

    mode_colors = {
        "Comfort": (92, 93, 87),
        "Sport": (190, 0, 0),
        "Sport+": (215, 0, 0),
        "ECO PRO": (0, 95, 215)
    }

    try: 
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
                elif event.type == pygame.KEYDOWN and event.key in mode_keys: 
                    with vehicle_state_lock:
                        vehicle_state.drive_mode = mode_keys[event.key]

            back_color = mode_colors.get(mode)
            if back_color is None: 
                print(f"[AVISO] drive_mode desconhecido: '{mode}'")
                back_color = (92, 93, 87)

            screen.fill(back_color)
            
            y = 50

            draw_arc_background(screen, "rpm", 600, 200, 90)
            draw_ticks(screen, "rpm", 600, 200, 90, font_small)
            draw_needle(screen, rpm, "rpm", 600, 200, 65)
            
            clock.tick(30)
            pygame.display.flip()
    except KeyboardInterrupt:
        print("\n BimmerDash encerrado pelo usuário...")
    finally: 
        stop_event.set()
        pygame.quit()
