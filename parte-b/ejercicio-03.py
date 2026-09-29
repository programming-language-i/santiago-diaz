### B3. Una excepción en el pool

"""
Muestra que si se lanza una excepción en un hilo del pool, el hilo principal no se bloquea y puede continuar su ejecución.
"""
from concurrent.futures import ThreadPoolExecutor


def dividir(a, b):
    return a / b


with ThreadPoolExecutor() as pool:
    futuro = pool.submit(dividir, 1, 0)
print("listo")