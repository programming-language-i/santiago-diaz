# Taller de refuerzo · Hilos, GIL y procesos — Sesiones 1 y 2

Práctica de refuerzo sobre lo visto en las clases: concurrencia vs. paralelismo, ciclo de vida del hilo, `join()`, el GIL, hilos por herencia, daemon, excepciones en hilos, `multiprocessing`.

- **Regla de trabajo:** en las Partes B y C, **primero escribir la predicción en papel y después ejecutar**. Quien ejecuta primero no practica nada.
- Todo el código está probado en Python 3.14 sobre Linux. Los tiempos cambian por máquina; lo que se compara es la relación entre ellos.

| Parte | Contenido |
| --- | --- |
| A. Conceptos | 8 preguntas cortas |
| B. Predecir la salida | 6 fragmentos |
| C. Encontrar el error | 4 fragmentos que fallan |
| D. ¿Hilos o procesos? | 6 escenarios |
| E. Programar | 2 ejercicios |

---

## Parte A — Conceptos

Responder en una o dos líneas.

1. Un programa atiende dos tareas alternando en un solo núcleo. ¿Es concurrencia, paralelismo o ambas? Es concurrencia como solo tiene un núcleo no hay una ejecución simultanea, solo intercalado.
2. Nombrar dos diferencias entre un proceso y un hilo *(memoria, costo, fallo)*. La diferencia es que el proceso tiene su propio espacio de memoria y es mucho más costoso de crear, mientras que un hilo comparten memoria con otros hilos del mismo proceso.
3. ¿En qué estado del ciclo de vida está un hilo que ejecuta `time.sleep(2)`? ¿Qué devuelve `is_alive()`? Está en estado dormido esperando algo el is_alive devuelve verdadero mientras ejecuta el sleep y falso cuando termina el hilo.
4. ¿Qué protege el GIL? ¿Evita las condiciones de carrera en los datos del programa? GIL protege el acceso al motor de python permitiendo que un solo hilo lo ejecute a la vez, pero no evita las condiciones de carrera en los datos de programación.
5. ¿Por qué 4 hilos que duermen 1 s cada uno tardan ~1 s en total y no ~0,25 s? Porque el time sleep libera el GIL permitiendo que los hilos duerman en paralelo y el tiempo total es igual al tiempo individual no a la suma.
6. Al crear un hilo por herencia, ¿qué método se sobrescribe y cuál nunca? ¿Por qué? Se sobre escribe el método run() pero nunca se sobreescribe el método start(), porque este crea el hilo del sistema operativo y se llama internamente run().
7. ¿Qué pasa con un hilo daemon cuando termina el hilo principal? ¿Qué **no** se ejecuta? No se ejecuta ningún bloque de código pendiente después de ese punto.
8. Completar la regla del curso: *hilos para , procesos para*. Los hilos para esperar y procesos para calcular.
---

## Parte B — Predecir la salida

Para cada fragmento: escribir la salida exacta *(o el tiempo aproximado, si se pide)*, ejecutar y explicar la diferencia si la hubo.

### B1. ¿Cuánto tarda?

```python
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
```

### B2. Daemon con `finally`

```python
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
```

### B3. Una excepción en el pool

```python
from concurrent.futures import ThreadPoolExecutor


def dividir(a, b):
    return a / b


with ThreadPoolExecutor() as pool:
    futuro = pool.submit(dividir, 1, 0)
print("listo")
```

### B4. Reiniciar un hilo

```python
import threading

hilo = threading.Thread(target=print, args=("hola",))
hilo.start()
hilo.join()
print(hilo.is_alive())
hilo.start()
```

### B5. Procesos y una lista global

```python
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
```

### B6. Estado por instancia y estado de clase

```python
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
```

---

## Parte C — Encontrar el error

Cada fragmento falla o no hace lo que su autor cree. Para cada uno:
**(1)** qué pasa al ejecutarlo
**(2)** por qué
**(3)** la corrección mínima.

### C1. Descarga por herencia

```python
import threading


class Descarga(threading.Thread):
    def __init__(self, archivo):
        self.archivo = archivo

    def run(self):
        print("descargando", self.archivo)


Descarga("a.zip").start()
```

### C2. Tres tareas "concurrentes"

```python
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
```

### C3. Un pool de procesos sin guarda

```python
from concurrent.futures import ProcessPoolExecutor


def cuadrado(n):
    return n * n


with ProcessPoolExecutor(max_workers=2) as pool:
    print(list(pool.map(cuadrado, range(4))))
```

---

## Parte D — ¿Hilos o procesos?

Para cada programa, elegir **hilos** o **procesos** y justificar en una línea *(¿espera o calcula?)*.

1. Consultar el precio de 30 productos en 30 APIs distintas.
2. Contar las palabras palíndromas de 10 libros ya cargados en memoria.
3. Un servidor de chat que atiende 15 clientes conectados.
4. Aplicar un filtro de desenfoque a 200 fotos, píxel por píxel, en Python puro.
5. Leer 50 archivos de log del disco y copiarlos a otra carpeta.
6. Simular 1.000.000 de lanzamientos de dados en 8 lotes y promediar.

---

## Parte E — Programar

Repositorio personal, carpeta `practica-clase/`, con un `README.md` que pegue las salidas obtenidas.

```bash
practica-clase/
├── primos.py
├── consultas.py
└── README.md
```

---

## Autoevaluación

Marcar antes de dar el taller por terminado:

- [ ] Explico con un ejemplo la diferencia entre concurrencia y paralelismo.
- [ ] Sé por qué `start()` y `join()` en el mismo bucle vuelven secuencial el programa.
- [ ] Sé qué hace y qué no hace el GIL.
- [ ] Creo un hilo por herencia con `super().__init__()` y `run()`, con estado por instancia.
- [ ] Sé qué se pierde al usar un hilo daemon.
- [ ] Recupero el resultado y la excepción de un hilo, con herencia y con pool.
- [ ] Sé por qué los procesos no ven la memoria del padre y por qué necesitan la guarda `if __name__ == "__main__":`.
- [ ] Elijo entre hilos y procesos preguntando si el programa espera o calcula.