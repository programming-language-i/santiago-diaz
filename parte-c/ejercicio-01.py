##Cada fragmento falla o no hace lo que su autor cree. Para cada uno:
##**(1)** qué pasa al ejecutarlo
##**(2)** por qué
##**(3)** la corrección mínima.

### C1. Descarga por herencia

"""
Se agrega el super().__init__(), el super es una funcion que llama al constructor de la clase padre osea thread
y se usa el init para ejecutar el constructor de la clase padre.
"""
import threading


class Descarga(threading.Thread):
    def __init__(self, archivo):
        super().__init__()
        self.archivo = archivo

    def run(self):
        print("descargando", self.archivo)


Descarga("a.zip").start()