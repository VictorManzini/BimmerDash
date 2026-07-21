import threading 
from time import sleep
from obd_reader import read_data
from ui import show_data

thread_read = threading.Thread(target = read_data)
thread_read.start()

show_data()