import math

gauge_config = {
    "rpm": {
        "min": 1000, 
        "max": 7000, 
        "tick_step": 1000, 
        "arc_start": 225,   #degrees, lower-left
        "arc_end": -45,     #degrees, lower-right
        "color_rule": "gradient",
        "critical_threshold": 6000 
    }
}

def angle_to_coordinate(angle_degrees, cx, cy, radius):
    angle_rad = math.radians(angle_degrees)
    x = cx + radius * math.cos(angle_rad)
    y = cy - radius * math.sin(angle_rad)
    return (x, y)

def value_to_color(value, config): 
    if config["color_rule"] is None: 
        return (255, 255, 255) #fixed white, no gradient
    # blue->green->red gradient goes here when handling temperature channels 
    return (255, 255, 255)

def value_to_fraction(value, minimum, maximum): 
    value = max(minimum, min(maximum, value))
    return (value - minimum) / (maximum - minimum)

def value_to_angle(value, minimum, maximum, arc_start, arc_end):
    ratio = value_to_fraction(value, minimum, maximum)
    angle = arc_start + ratio * (arc_end - arc_start)
    return angle

def value_to_color(value, config):
    if config["color_rule"] is None: 
        return (255, 255, 255)
    
    threshold = config["critical_threshold"]
    minimum = config["min"]
    midpoint = (minimum + threshold) / 2

    if value <= minimum: 
        return(0, 0, 255)
    if value >= threshold: 
        return(255, 0, 0)

    if value < midpoint: 
        ratio = (value - minimum) / (midpoint - minimum) 
        r = int(0 + (0 - 0) * ratio)
        g = int(0 + (255 + 0) * ratio) 
        b = int(255 + (0 - 255) * ratio)
        return (r, g, b)
    else:
        ratio = (value - midpoint) / (threshold - midpoint)
        r = int(0 + (255 - 0) * ratio)
        g = int(255 + (0 - 255) * ratio)
        b = int(0 + (0 - 0) * ratio)
        return (r, g, b)
