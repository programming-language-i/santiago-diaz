# Guía paso a paso · Persistencia funcional del chat

Guía para los equipos: llevar la persistencia del proyecto (el `mensajes.log` que escribe el servidor desde el Hito 2) al estilo de la Unidad 3, con **funciones puras** y **funciones de orden superior**, y dejar lista la lectura del log para el Hito 3.

- **Cuándo:** laboratorio de la Clase 10 (35 min), pasos 0, 1, 2, 3 y 5. Los pasos 4, 6, 7 y 8 siguen en el TI como parte del Hito 3.
- **Cómo:** en equipo, sobre el repositorio del proyecto, con el responsable de cada paso anotado en la tabla de responsables.
- **Los ejemplos no son el hito resuelto.** Cada paso se muestra sobre otro dato, los **movimientos de bodega** del centro de distribución (`Movimiento`: producto, bodega, cantidad, hora), y el equipo lo traslada a sus `Mensaje` y `Registro`. Las verificaciones con `assert` sí se copian y se adaptan.
- **El contrato no cambia:** módulos de la sección 4 y log JSON Lines de la sección 5 del [[uniremington/programming-languages-i/project/statement|Enunciado del proyecto]].

## La idea: los efectos viven en el borde

```
escritura:  Mensaje ─(puro: a_json)→ cola ─→ escritor (efecto: archivo)
lectura:    archivo (efecto: abrir) ─→ map(desde_linea) ─→ filter ─→ métricas puras ─→ reporte (efecto: imprimir)
```

- **Pura:** mismo argumento, mismo resultado, y no toca nada fuera de sí misma.
- **Efecto:** abrir o escribir un archivo, enviar por la red, imprimir, `datetime.now()`, mutar un argumento o una global.
- **La regla de la guía:** cada efecto vive en **una sola** función del borde; todo lo demás es puro y se prueba con un `assert`, sin servidor, sin archivo y sin hilos.

---

## Paso 0 · Ubicar el borde

Llenar esta tabla en el `README.md` con las funciones que ya tiene el proyecto:

| Módulo | Función | ¿Toca archivo, red, pantalla o reloj? | ¿Pura? |
|---|---|---|---|
| `mensaje.py` | `a_json` | | |
| `conexion.py` | la que pone `emisor` y `timestamp` | | |
| `persistencia.py` | el escritor | | |
| … | | | |

- **Lo esperado:** `a_json` y `desde_json` puras; poner el `timestamp` es un efecto (lee el reloj) y vive en `conexion.py`; el escritor es el borde de la escritura.
- **Si `a_json` llama a `datetime.now()`**, no es pura: dos llamadas dan resultados distintos. El `timestamp` se pone **una vez**, al recibir, y viaja dentro del mensaje.

## Paso 1 · Serializar sin efectos *(8 min, en clase)*

**En el proyecto:** `Mensaje.a_json(self) -> str`, del Hito 2. Se revisa que sea pura: no abre nada, no imprime y no lee el reloj.

**Ejemplo:**

```python
import json
from datetime import datetime
from typing import NamedTuple


class Movimiento(NamedTuple):
    producto: str
    bodega: str
    cantidad: int  # positiva: entrada; negativa: salida
    timestamp: datetime


def a_linea(m: Movimiento) -> str:
    return json.dumps(
        {
            "producto": m.producto,
            "bodega": m.bodega,
            "cantidad": m.cantidad,
            "timestamp": m.timestamp.isoformat(timespec="seconds"),
        },
        ensure_ascii=False,
    )
```

**Verificación:**

```python
m = Movimiento("cajas", "norte", 5, datetime(2026, 10, 20, 18, 42, 7))
assert a_linea(m) == a_linea(m)  # mismo argumento, mismo resultado
assert "\n" not in a_linea(m)  # JSON Lines: una línea por objeto
```

- **`ensure_ascii=False`:** sin él, `recepción` se guarda como `recepción`. El log es UTF-8 (sección 5).
- **Error típico:** devolver la línea **y además** escribirla. Serializar y escribir son dos funciones.

## Paso 2 · Leer una línea sin lanzar *(10 min, en clase)*

**En el proyecto:** en `analisis/lectura.py`, el `Registro` del Hito 3 (`NamedTuple` con `tipo`, `emisor`, `canal`, `destino`, `contenido` y `timestamp` como `datetime`) y `desde_linea(linea: str) -> Registro | None`. Una línea dañada devuelve `None`; no lanza y no imprime.

**Ejemplo:**

```python
def desde_linea(linea: str) -> Movimiento | None:
    try:
        datos = json.loads(linea)
        return Movimiento(
            producto=datos["producto"],
            bodega=datos["bodega"],
            cantidad=int(datos["cantidad"]),
            timestamp=datetime.fromisoformat(datos["timestamp"]),
        )
    except json.JSONDecodeError, KeyError, TypeError, ValueError:
        return None
```

**Verificación:**

```python
assert desde_linea(a_linea(m)) == m  # ida y vuelta
for mala in ["", "{", "5", "[]", '{"producto": "x"}']:
    assert desde_linea(mala) is None, mala
```

- **Por qué cuatro excepciones:** `"{"` da `JSONDecodeError`; un campo que falta, `KeyError`; `"5"` o `"[]"` no son diccionarios, `TypeError`; una hora mal escrita, `ValueError`.
- **En el proyecto, `canal` o `destino` es `None`** según el `tipo`: `datos.get("canal")`, no `datos["canal"]`.
- **Error típico:** `except Exception: print("línea dañada")`. Imprimir es un efecto y esconde errores propios.

## Paso 3 · Decidir qué se guarda con un predicado *(4 min, en clase)*

**En el proyecto:** en `persistencia.py`, una función pura `se_guarda(...) -> bool` que es verdadera solo para `mensaje` y `privado` (sección 5: `unirse`, `dejar` y `error` no se guardan).

**Ejemplo:**

```python
def es_salida(m: Movimiento) -> bool:
    return m.cantidad < 0
```

**Verificación:**

```python
assert es_salida(m._replace(cantidad=-2))
assert not es_salida(m)
```

- **Los tipos que se guardan como constante inmutable:** `TIPOS_GUARDADOS = frozenset({"mensaje", "privado"})`. Una constante inmutable no es estado global: nadie la puede cambiar.
- **`m._replace(...)`** devuelve **otro** `NamedTuple`; `m` no cambia.

## Paso 4 · El escritor recibe funciones *(TI)*

**En el proyecto:** el hilo escritor de `persistencia.py` (cola, un solo hilo, no `daemon`, centinela `None`) recibe **como parámetros** la función que serializa y la que decide qué se guarda. Es una función de orden superior, como `threading.Thread(target=...)`.

**Ejemplo:**

```python
import queue
from collections.abc import Callable


def escribir(
    cola: "queue.Queue[Movimiento | None]",
    ruta: str,
    serializar: Callable[[Movimiento], str],
    se_guarda: Callable[[Movimiento], bool],
) -> None:
    with open(ruta, "a", encoding="utf-8") as archivo:
        while (m := cola.get()) is not None:
            if se_guarda(m):
                archivo.write(serializar(m) + "\n")
```

**Verificación:** el escritor se prueba con una cola, un archivo temporal y sin servidor.

```python
import os, tempfile, threading

with tempfile.TemporaryDirectory() as d:
    ruta = os.path.join(d, "movimientos.log")
    cola: "queue.Queue[Movimiento | None]" = queue.Queue()
    hilo = threading.Thread(target=escribir, args=(cola, ruta, a_linea, es_salida))
    hilo.start()
    for i in range(10):
        cola.put(m._replace(cantidad=-(i + 1)))  # 10 salidas
    cola.put(m)  # una entrada: no se guarda
    cola.put(None)
    hilo.join()
    with open(ruta, encoding="utf-8") as f:
        assert sum(1 for _ in f) == 10
```

- **Lo que se gana:** el escritor ya no sabe qué es un `Mensaje` ni qué tipos se guardan; esa decisión vive en dos funciones puras que se prueban solas.
- **Sirve para la sustentación:** «por qué una `Queue` y un solo escritor» es una de las tres decisiones de diseño del guion (sección 7).
- **Error típico:** abrir el archivo desde el hilo de cada cliente, o un escritor `daemon` que muere sin vaciar la cola. Los dos ya se penalizaron en el Hito 2.

## Paso 5 · De líneas a registros con `map` y `filter` *(8 min, en clase)*

**En el proyecto:** en `analisis/lectura.py`, `registros(lineas: Iterable[str]) -> Iterator[Registro]`. Recibe **líneas**, no una ruta: así es pura y se prueba con una lista.

**Ejemplo:**

```python
from collections.abc import Iterable, Iterator


def movimientos(lineas: Iterable[str]) -> Iterator[Movimiento]:
    return filter(None, map(desde_linea, lineas))
```

**Verificación:**

```python
lineas = [a_linea(m), "basura", a_linea(m._replace(bodega="sur", cantidad=-2))]
flujo = movimientos(lineas)
assert not isinstance(flujo, list)  # perezoso: todavía no leyó nada
assert len(tuple(flujo)) == 2  # la línea dañada se omite
```

- **`map(desde_linea, ...)`** aplica una función que ya existe: es el caso en que `map` gana a la comprehension.
- **`filter(None, ...)`** se queda con lo que no es `None`. Funciona porque un `NamedTuple` con campos siempre es verdadero.
- **`map` y `filter` son perezosos:** procesan una línea cada vez que alguien pide la siguiente. En la Clase 11 esta función queda dentro del generador `leer_mensajes(ruta)`, el único que abre el archivo.

## Paso 6 · Métricas puras *(TI)*

**En el proyecto:** `analisis/metricas.py`, sin `global`, sin abrir archivos y sin imprimir. Cada métrica recibe un `Iterable[Registro]` y devuelve un valor.

**Ejemplo:** tres métricas de bodega con una herramienta distinta cada una.

```python
from collections import Counter
from functools import partial, reduce
from operator import attrgetter


def por_bodega(movs: Iterable[Movimiento]) -> Counter[str]:
    return Counter(map(attrgetter("bodega"), movs))  # map con una función ya hecha


def en_bodega(bodega: str, m: Movimiento) -> bool:
    return m.bodega == bodega


del_norte = partial(en_bodega, "norte")  # una función nueva a partir de otra


def sumar_unidades(acc: dict[str, int], m: Movimiento) -> dict[str, int]:
    return {**acc, m.producto: acc.get(m.producto, 0) + m.cantidad}


def existencias(movs: Iterable[Movimiento]) -> dict[str, int]:
    return reduce(sumar_unidades, movs, {})  # el acumulador es un dict, no una suma


def productos(movs: Iterable[Movimiento]) -> list[str]:
    return sorted({m.producto for m in movs})  # comprehension: sin lambda de por medio
```

**Verificación:**

```python
movs = tuple(
    movimientos(lineas + [a_linea(m._replace(producto="estibas", cantidad=3))])
)
antes = list(movs)
assert por_bodega(movs) == {"norte": 2, "sur": 1}
assert len(list(filter(del_norte, movs))) == 2
assert existencias(movs) == existencias(movs) == {"cajas": 3, "estibas": 3}
assert productos(movs) == ["cajas", "estibas"]
assert list(movs) == antes  # ninguna métrica modificó los datos
```

**Las métricas del Hito 3** quedan para el equipo. Pistas, no soluciones:

| Métrica | Firma | Pista |
|---|---|---|
| `top_emisores` | `(registros: Iterable[Registro], n: int) -> list[tuple[str, int]]` | El mismo patrón que `por_bodega`, y `Counter.most_common` |
| `mensajes_por_hora` | `(registros: Iterable[Registro]) -> dict[int, int]` | La clave es `timestamp.hour`; el `timestamp` ya es `datetime` desde el paso 2 |
| `palabras_frecuentes` | `(registros: Iterable[Registro], n: int) -> list[tuple[str, int]]` | Una comprehension que aplana contenidos en palabras, `str.lower` y quitar puntuación |

- **`reduce` con `{**acc, ...}`** copia el diccionario en cada paso: con 100.000 mensajes es lento. `Counter` hace lo mismo sin copiar. Se elige con una medición, no por ser «más funcional».

## Paso 7 · El reporte, único que imprime *(TI)*

**En el proyecto:** `analisis/reporte.py` abre (a través de `leer_mensajes`), llama a las métricas e imprime. No calcula nada.

**Ejemplo:**

```python
def reporte(ruta: str) -> None:
    with open(ruta, encoding="utf-8") as archivo:
        movs = tuple(movimientos(archivo))
    print("Por bodega:", dict(por_bodega(movs)))
    print("Existencias:", existencias(movs))
```

- **El `tuple(...)` del ejemplo materializa el archivo** para recorrerlo dos veces. Sirve hoy, con un log pequeño. **En el Hito 3 no pasa la lista de verificación** (`list(...)` en el camino de lectura): en la Clase 11 se cambia por un recorrido por métrica o por `itertools.tee`, y el equipo justifica la elección con una medición (punto 4 del Hito 3).

## Paso 8 · Verificar la pureza *(TI)*

Un `prueba_persistencia.py` del equipo, en la raíz del repositorio, con estas comprobaciones sobre su propio código:

1. **Ida y vuelta:** `desde_linea(mensaje.a_json())` reconstruye los mismos campos.
2. **Mismo argumento, mismo resultado:** cada función de `metricas.py` llamada dos veces seguidas sobre una **tupla** da lo mismo.
3. **Los datos no cambian:** la tupla de registros es igual antes y después de calcular las tres métricas.
4. **Líneas dañadas:** un log con dos líneas rotas produce dos registros menos y ninguna excepción.
5. **Extremo a extremo:** servidor con dos clientes, 10 mensajes, `unirse` y un `error`; detener el servidor y contar **10 líneas** en `datos/mensajes.log`.
6. **`mypy mensajeria` sin errores** y sin `Any`.