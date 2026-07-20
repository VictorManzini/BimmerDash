import pygame
import math
import pygame.gfxdraw
from gauges import gauge_config, value_to_angle, angle_to_coordinate, value_to_fraction, value_to_color
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
    tail_lenght = radius * 0.28
    angle_back = angle + 180
    tail_tip = angle_to_coordinate(angle_back, cx, cy, tail_lenght)
    polygon = [tip, base_right, tail_tip, base_left]

    pygame.gfxdraw.filled_polygon(screen, polygon, arc_color)
    pygame.gfxdraw.aapolygon(screen, polygon, arc_color)

    pygame.gfxdraw.filled_circle(screen, cx, cy, 9, (30, 30, 30))
    pygame.gfxdraw.filled_circle(screen, cx, cy, 9, (30, 30, 30))

    pygame.gfxdraw.filled_circle(screen, cx, cy, 4, arc_color)
    pygame.gfxdraw.aacircle(screen, cx, cy, 4, arc_color)

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

def draw_ring_arc(screen, cx, cy, radius, thickness, start_deg, end_deg, arc_min, arc_max, color):
    steps = 60
    step_value = (arc_max - arc_min) / steps 
    outer_points = []
    inner_points = []
    for i in range(steps + 1):
        value = arc_min + i * step_value
        angle = value_to_angle(value, arc_min, arc_max, start_deg, end_deg)
        outer_point = angle_to_coordinate(angle, cx, cy, radius + thickness / 2)
        outer_points.append(outer_point)
        inner_point = angle_to_coordinate(angle, cx, cy, radius - thickness / 2)
        inner_points.append(inner_point)
    inner_points.reverse()
    polygon = outer_points + inner_points
    pygame.gfxdraw.filled_polygon(screen, polygon, color)
    pygame.gfxdraw.aapolygon(screen, polygon, color)

def draw_value_arc(screen, value, channel, cx, cy, radius, thickness, font):
    config = gauge_config[channel]

    draw_ring_arc(screen, cx, cy, radius, thickness, 
                  config["arc_start"], config["arc_end"], 
                  config["min"], config["max"], (80,80,80))
    
    fraction = value_to_fraction(value, config["min"], config["max"])
    angle = config["arc_start"] + fraction * (config["arc_end"] - config["arc_start"])
    color = value_to_color(value, config)

    draw_ring_arc(screen, cx, cy, radius, thickness, 
                  config["arc_start"], angle, 
                  config["min"], config["max"], color)
    
    if config["decimals"] == 0:
        text = f"{int(round(value))}" # text é o nome da variavel, o que vai dentro dela é o que vai ser printado no display pelo pygame
    else: 
        text = f"{round(value, config['decimals'])}"
    label = font.render(text, True, (255, 255, 255)) #label é quem vai renderizar o texto com cor
    screen.blit(label, label.get_rect(center=(cx, cy))) #screen.blit é responsável por printar e por dar as coordenadas de onde o pygame deve printar o texto desejado  
    text2 = channel
    label2 = font.render(text2, True, (255, 255, 255))
    screen.blit(label2, label2.get_rect(center=(cx, cy+20)))
    
    
def draw_danger_zone(screen, channel, cx, cy, radius, thickness):
    config = gauge_config[channel]
    danger_color = (200, 40, 40)
    threshold = config["critical_threshold"]
    steps = 60
    step_value = (config["max"] - threshold) / steps 
    outer_points = []
    inner_points = []
    for i in range(steps + 1):
        value = (threshold + i * step_value)
        angle = value_to_angle(value, config["min"], config["max"], config["arc_start"], config["arc_end"])
        outer_point = angle_to_coordinate(angle, cx, cy, radius + thickness / 2)
        outer_points.append(outer_point)
        inner_point = angle_to_coordinate(angle, cx, cy, radius - thickness / 2)
        inner_points.append(inner_point)
    inner_points.reverse()
    polygon = outer_points + inner_points
    pygame.gfxdraw.filled_polygon(screen, polygon, danger_color)
    pygame.gfxdraw.aapolygon(screen, polygon, danger_color)
    
def draw_bar(screen, value, channel, x, y, width, height): 
    config = gauge_config[channel]
    bar_color = value_to_color(value, config)
    track_color = (80,80,80)
    pygame.draw.rect(screen, track_color, pygame.Rect(x, y, width, height))
    fraction = value_to_fraction(value, config["min"], config["max"])
    fill_height = int(height * fraction)
    fill_y = y + (height - fill_height)
    pygame.draw.rect(screen, bar_color, pygame.Rect(x, fill_y, width, fill_height))

def get_slot_position(index, screen_width, screen_height, rows, cols):
    cell_width = screen_width / cols
    cell_height = screen_height / rows
    row = index // cols 
    col = index % cols

    cx = col * cell_width + cell_width / 2
    cy = row * cell_height + cell_height / 2
    return cx, cy
    
def show_data():
    pygame.init()
    screen = pygame.display.set_mode((800, 480))
    font = pygame.font.Font(None, 26)
    font_small = pygame.font.Font(None, 16)
    clock = pygame.time.Clock()
    running = True
    back_color = (92, 93, 87)
    text_color = (255, 255, 255)
    rpm_config = gauge_config["rpm"]

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
            
            draw_ring_arc(screen, 600, 200, 90, 5, rpm_config["arc_start"], rpm_config["arc_end"], rpm_config["min"], rpm_config["max"], (255, 255, 255))
            draw_danger_zone(screen, "rpm", 600, 200, 90, 8)
            draw_ticks(screen, "rpm", 600, 200, 90, font_small)
            draw_needle(screen, rpm, "rpm", 600, 200, 65)
            draw_bar(screen, rpm, "rpm", 300, 100, 40, 250)
            draw_value_arc(screen, rpm, "rpm", 200, 350, 80, 8, font)
            
            clock.tick(30)
            pygame.display.flip()
    except KeyboardInterrupt:
        print("\n BimmerDash encerrado pelo usuário...")
    finally: 
        stop_event.set()
        pygame.quit()
