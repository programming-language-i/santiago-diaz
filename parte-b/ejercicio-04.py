### B4. Reiniciar un hilo

"""
El hilo imprime un hola y termina, luego de eso se intenta reiniciar el hilo otra vez pero no es posible,
porque un hilo no se puede reiniciar una vez terminado.
"""
import threading

hilo = threading.Thread(target=print, args=("hola",))
hilo.start()
hilo.join()
print(hilo.is_alive())
hilo.start()