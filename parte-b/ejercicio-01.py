### B1. ¿Cuánto tarda?
"""
Tarda 3 segundos en ejectarse, ya que cada hilo se ejecuta de maenera secuencial, hay que esperar que cada hilo termine para que se
ejecute el siguiente.
"""
import threading
import time


def tarea(n):
    time.sleep(1)


inicio = time.perf_counter()
for i in range(3):
    hilo = threading.Thread(target=tarea, args=(i,))
    hilo.start()
    hilo.join()
print(f"{time.perf_counter() - inicio:.1f} s")