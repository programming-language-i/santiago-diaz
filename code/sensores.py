import threading
import time


def sensor(numero, temperatura):

    for i in range(5):
        print("Sensor", numero, "-> Temperatura:", temperatura, "°C")
        time.sleep(1)


hilo1 = threading.Thread(target=sensor, args=(1, 70))
hilo2 = threading.Thread(target=sensor, args=(2, 80))
hilo3 = threading.Thread(target=sensor, args=(3, 90))

hilo1.start()
hilo2.start()
hilo3.start()

hilo1.join()
hilo2.join()
hilo3.join()
