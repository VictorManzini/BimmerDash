from time import sleep
import threading
import random
from models import engine, vehicle_state, engine_lock, vehicle_state_lock

#directions = {"turbo": 1, "rpm": 1, "oil": 1, "water": 1, "transmission": 1, "speed": 1, "voltage": 1}

def update_sensor(obj, atributo, direcoes, chave, minimo, maximo, passo):
    valor = getattr(obj, atributo) + (direcoes[chave] * passo)
    if valor >= maximo or valor <= minimo:
        direcoes[chave] *= -1
    setattr(obj, atributo, valor)

def read_data():
    directions = {"turbo": 1, "rpm": 1, "oil": 1, "water": 1, "transmission": 1, "speed": 1, "voltage": 1}
    while True: 
        with engine_lock: 
            update_sensor(engine, "turbo_pressure", directions, "turbo", 0, 19, 1)
            update_sensor(engine, "rpm", directions, "rpm", 1, 7, 1)
            update_sensor(engine, "oil_temp", directions, "oil", 40, 100, 1)
            update_sensor(engine, "water_temperature", directions, "water", 45, 95, 1)
            update_sensor(engine, "transmission_temperature", directions, "transmission", 80, 95, 1)
            engine.fuel_consumption = random.uniform(2.0, 10.0)

        with vehicle_state_lock: 
            update_sensor(vehicle_state, "speed", directions, "speed", 0, 90, 1)
            update_sensor(vehicle_state, "battery_voltage", directions, "voltage", 12.0, 13.5, 0.05)
            vehicle_state.drive_mode = random.choice(["Sport +", "Sport", "Comfort", "ECO PRO"])
        sleep(0.2)








'''
def read_data():
    while True:
        for i in range(0, 19):
            with engine_lock: 
                engine.turbo_pressure = i
            #print(f"Pressão de turbina: {engine.read_boost():.2f}psi")
            sleep(0.2)
        for i in range(19, -1, -1):
            with engine_lock: 
                engine.turbo_pressure = i 
            #print(f"Pressão de turbina: {engine.read_boost():.2f}psi")
            sleep(0.2)
        
        for i in range(0, 7):
            with engine_lock: 
                engine.rpm = i * 1000
            #print(f"RPM: {engine.rpm:.0f}")
            sleep(0.2)
        for i in range(7, 0, -1):
            with engine_lock: 
                engine.rpm = i * 1000
            #print(f"RPM: {engine.rpm:.0f}")
            sleep(0.2)

        for i in range(40, 100):
            with engine_lock: 
                engine.oil_temp = i 
            #print(f"Temperatura do óleo: {engine.oil_temp:.2f}ºC")
            sleep(0.1)
        for i in range(100, 39, -1):
            with engine_lock: 
                engine.oil_temp = i 
            #print(f"Temperatura do óleo: {engine.oil_temp:.2f}ºC")
            sleep(0.1)
            
        for i in range(45, 95):
            with engine_lock: 
                engine.water_temperature = i
            #print(f"Temperatura da água: {engine.water_temperature:.2f}ºC")
            sleep(0.1)
        for i in range(95, 44, -1):
            with engine_lock:
                engine.water_temperature = i
            #print(f"Temperatura da água: {engine.water_temperature:.2f}ºC")
            sleep(0.1)

        for i in range(80, 95):
            with engine_lock: 
                engine.transmission_temperature = i
            #print(f"Temperatura do câmbio: {engine.transmission_temperature:.2f}ºC")
            sleep(0.1)
        for i in range(95, 79, -1):
            with engine_lock:
                engine.transmission_temperature = i 
            #print(f"temperatura do câmbio: {engine.transmission_temperature:.2f}ºC")
            sleep(0.1)

        with engine_lock:
            engine.fuel_consumption = random.uniform(2.0, 10.0)
        #print(f"Consumo de combustível atual: {engine.fuel_consumption:.1f}Km/L")
        sleep(0.3)
            
        with vehicle_state_lock: 
            vehicle_state.speed = random.uniform(0, 90)
        #print(f"Velocidade: {vehicle_state.speed:.0f}Km/h")
        sleep(0.3)

        with vehicle_state_lock: 
            vehicle_state.battery_voltage = random.uniform(12.0, 13.5)
        #print(f"Voltagem da bateria: {vehicle_state.battery_voltage:.1f}V")
        sleep(0.3)

        with vehicle_state_lock: 
            vehicle_state.drive_mode = random.choice(["Comfort", "Sport", "Sport +", "ECO PRO"])
        #print(f"Modo de condução {vehicle_state.drive_mode}")
        sleep(0.3)'''