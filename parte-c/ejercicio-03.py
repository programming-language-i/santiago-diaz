### C3. Un pool de procesos sin guarda

"""
El error era en que falta proteger la creación del ProcessPoolExecutor con el if __name__ == "__main__":,
Como el ProcessPoolExecutor está fuera de la protección, los procesos hijos intentan crear nuevamente otros procesos.
Esto puede provocar que los procesos se creen repetidamente y Python genere un error.
"""

from concurrent.futures import ProcessPoolExecutor

def cuadrado(n):
    return n * n

if __name__ == "__main__":
 with ProcessPoolExecutor(max_workers=2) as pool:
    print(list(pool.map(cuadrado, range(4))))