### B6. Estado por instancia y estado de clase

"""
El total es un atributo de instancia, por lo que cada hilo tiene su propio contador y ambos terminan en 3,
en cambio eventos es un atributo de clase compartido por dos instancias, por lo que se agregan 6 eventos en total.
"""

import threading


class Contador(threading.Thread):
    eventos = []

    def __init__(self, nombre):
        super().__init__(name=nombre)
        self.total = 0

    def run(self):
        for _ in range(3):
            self.total += 1
            self.eventos.append(self.name)


a, b = Contador("a"), Contador("b")
for h in (a, b):
    h.start()
for h in (a, b):
    h.join()
print(a.total, b.total, len(a.eventos))