from time import sleep
import threading
import random
from models import engine, vehicle_state, engine_lock, vehicle_state_lock, stop_event

def update_sensor(obj, attribute, directions, key, minimum, maximum, step):
    value = getattr(obj, attribute) + (directions[key] * step)
    if value >= maximum:
        value = maximum
        directions[key] *= -1
    elif value <= minimum:
        value = minimum
        directions[key] *= -1
    setattr(obj, attribute, value)  

def read_data():
    directions = {"turbo": 1, "rpm": 1, "oil": 1, "water": 1, "transmission": 1, "speed": 1, "voltage": 1}
    while not stop_event.is_set(): 
        with engine_lock: 
            update_sensor(engine, "turbo_pressure", directions, "turbo", 0.0, 1.9, 0.1)
            update_sensor(engine, "rpm", directions, "rpm", 1000, 7000, 100)
            update_sensor(engine, "oil_temp", directions, "oil", 40, 100, 1)
            update_sensor(engine, "water_temperature", directions, "water", 45, 95, 1)
            update_sensor(engine, "transmission_temperature", directions, "transmission", 80, 95, 1)
            engine.fuel_consumption = random.uniform(2.0, 10.0)

        with vehicle_state_lock: 
            update_sensor(vehicle_state, "speed", directions, "speed", 0, 90, 1)
            update_sensor(vehicle_state, "battery_voltage", directions, "voltage", 12.0, 13.5, 0.05)
        sleep(0.2)
