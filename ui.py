from time import sleep
from models import engine, vehicle_state, engine_lock, vehicle_state_lock

def show_data():
    while True: 
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

        print(f"Turbo pressure: {turbo:.1f}psi | RPM: {rpm:.0f} | Oil temperature: {oil:.1f}ºC | Engine temperature: {water:.1f}ºC | Gearbox temperature: {transmission}ºC | Fuel consumption: {fuel:.1f}Km/L | Speed: {speed:.0f}Km/h | Bat: {voltage:.1f}V | Mode: {mode}")
        sleep(0.5)