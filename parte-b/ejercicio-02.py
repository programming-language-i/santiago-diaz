### B2. Daemon con `finally`

"""
El demon true sirve para que el hilo no se ejecute de manera secuencial, es el hilo principal el que decide cuando
 termina la ejecución del programa.
 Y el finally se ejecuta cuando el hilo termina, aunque el hilo principal haya terminado antes.
"""
import threading
import time


def guardar():
    try:
        time.sleep(2)
        print("guardado")
    finally:
        print("archivo cerrado")

threading.Thread(target=guardar, daemon=True).start()
time.sleep(0.5)
print("fin")