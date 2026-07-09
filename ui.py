import pygame
import math
import pygame.gfxdraw
from gauges import gauge_config, value_to_angle, angle_to_coordinate
from models import engine, vehicle_state, engine_lock, vehicle_state_lock, stop_event

def draw_needle(screen, value, channel, cx, cy, radius):
    config = gauge_config[channel]
    arc_color = (255, 0, 0)
    angle = value_to_angle(value, config["min"], config["max"], config["arc_start"], config["arc_end"])

    angle_rad = math.radians(angle)
    perp_rad = angle_rad + math.pi / 2
    base_width = 6

    tip = angle_to_coordinate(angle, cx, cy, radius)

    base_left = (cx + math.cos(perp_rad) * base_width, cy - math.sin(perp_rad) * base_width)
    base_right = (cx - math.cos(perp_rad) * base_width, cy + math.sin(perp_rad) * base_width)

    polygon = [tip, base_left, base_right]

    pygame.gfxdraw.filled_polygon(screen, polygon, arc_color)
    pygame.gfxdraw.aapolygon(screen, polygon, arc_color)

    pygame.gfxdraw.filled_circle(screen, cx, cy, 6, arc_color)
    pygame.gfxdraw.aacircle(screen, cx, cy, 6, arc_color)

def draw_ticks(screen, channel, cx, cy, radius, font_small):
    arc_color = (255, 255, 255)
    config = gauge_config[channel]
    value = config["min"]
    while value <= config["max"]: 
        angle = value_to_angle(value, config["min"], config["max"], config["arc_start"], config["arc_end"])
        p_out = angle_to_coordinate(angle, cx, cy, radius)
        p_in = angle_to_coordinate(angle, cx, cy, radius -15)
        p_label = angle_to_coordinate(angle, cx, cy, radius - 40)
        pygame.draw.aaline(screen, arc_color, p_in, p_out, 3)
        label = font_small.render(str(int(value)), True, arc_color)
        screen.blit(label, label.get_rect(center=p_label))
        value += config["tick_step"]

def draw_ring_arc(screen, channel, cx, cy, radius, thickness): 
    arc_color = (255, 255, 255)
    config = gauge_config[channel]
    steps = 60
    step_value = (config["max"] - config["min"]) / steps 

    outer_points = []
    inner_points = []

    for i in range(steps + 1): 
        value = (config["min"] + i * step_value)
        angle = value_to_angle(value, config["min"], config["max"], config["arc_start"], config["arc_end"])
        outer_point = angle_to_coordinate(angle, cx, cy, radius + thickness / 2) 
        outer_points.append(outer_point)
        inner_point = angle_to_coordinate(angle, cx, cy, radius - thickness / 2)
        inner_points.append(inner_point)

    inner_points.reverse()
    polygon = outer_points + inner_points 
    pygame.gfxdraw.filled_polygon(screen, polygon, arc_color)
    pygame.gfxdraw.aapolygon(screen, polygon, arc_color)
    
def show_data():
    pygame.init()
    screen = pygame.display.set_mode((800, 480))
    font_small = pygame.font.Font(None, 16)
    clock = pygame.time.Clock()
    running = True
    back_color = (92, 93, 87)
    text_color = (255, 255, 255)

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
            
            draw_ring_arc(screen, "rpm", 600, 200, 90, 5)
            draw_ticks(screen, "rpm", 600, 200, 90, font_small)
            draw_needle(screen, rpm, "rpm", 600, 200, 65)
            
            clock.tick(30)
            pygame.display.flip()
    except KeyboardInterrupt:
        print("\n BimmerDash encerrado pelo usuário...")
    finally: 
        stop_event.set()
        pygame.quit()
