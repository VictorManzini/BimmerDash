import threading 
from time import sleep
from obd_reader import read_data

thread_engine = threading.Thread(target = read_data)

thread_engine.start()