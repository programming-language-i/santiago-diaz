## B5. Procesos y una lista global

"""
Aquí la lista de resultados es global, pero los procesos no comparten la misma memoria, es decir, cada proceso modifica su propia
copia de la lista, por lo que al final los cambios no llegan al proceso principal y este imprime una lista vacía.
"""
import multiprocessing

resultados = []


def calcular(n):
    resultados.append(n * n)


if __name__ == "__main__":
    procesos = [multiprocessing.Process(target=calcular, args=(n,)) for n in range(4)]
    for p in procesos:
        p.start()
    for p in procesos:
        p.join()
    print(resultados)