import threading 
from time import sleep
from obd_reader import read_data
from ui import show_data

thread_engine = threading.Thread(target = read_data)
thread_ui = threading.Thread(target = show_data)

thread_engine.start()
thread_ui.start()