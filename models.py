import threading

class PowerTrain: 
    #All engine sensors are gonna be inside this class
    def __init__(self):
        self.turbo_pressure = 0.0
        self.rpm = 750
        self.oil_temp = 70
        self.water_temperature = 50.0
        self.fuel_consumption = 0 #Km/L 
        self.transmission_temperature = 0.0

    #Turbo Pressure
    def read_boost(self):
        return self.turbo_pressure / 10
    
class VehicleState:
    #Everything that is independent of the power train
    
    def __init__(self):
        self.speed = 0
        self.drive_mode = "comfort" #BMW's driving mode that affects the power train and the suspensions
        self.battery_voltage = 12.0

engine = PowerTrain()
vehicle_state = VehicleState()

engine_lock = threading.Lock()
vehicle_state_lock = threading.Lock()
