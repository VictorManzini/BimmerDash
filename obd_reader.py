from time import sleep
import threading
import random
from models import engine, vehicle_state, engine_lock, vehicle_state_lock

















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