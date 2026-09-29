import threading
import time

def sensor(numero, temperatura):
    print(f"{numero} sensor")

    for i in range(5):
        print(f"{numero} - {i+1}: temperatura: {temperatura} grados centigrados")
        time.sleep(1)

    print("termino")

if __name__ == "__main__":
    threads = [
        threading.Thread(target=sensor, args=("Sensor 1", 70)),
        threading.Thread(target=sensor, args=("Sensor 2", 80)),
        threading.Thread(target=sensor, args=("Sensor 3", 90)),
        threading.Thread(target=sensor, args=("Sensor 4", 50)),
        threading.Thread(target=sensor, args=("Sensor 5", 60)),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    print("Finalizo el proceso")