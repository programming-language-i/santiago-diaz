### C2. Tres tareas "concurrentes"

"""Se sobrescribió start() en vez de run(). Eso impide que se 
   cree un hilo real, entonces el código corre uno por uno en 
   el hilo principal (~3s), y t.join() falla porque el hilo 
   nunca se marcó como iniciado. """

import threading
import time


class Tarea(threading.Thread):
    def start(self):                      
        time.sleep(1)
        print(self.name, "lista")


inicio = time.perf_counter()
tareas = [Tarea(name=f"t{i}") for i in range(3)]
for t in tareas:
    t.start()
print(f"{time.perf_counter() - inicio:.1f} s")
for t in tareas:
    t.join()