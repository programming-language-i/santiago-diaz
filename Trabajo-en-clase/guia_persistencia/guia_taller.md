# Persistencia paso a paso

Guía para construir, desde cero, la base de persistencia de cualquier programa: guardar registros en un archivo, leerlos de vuelta y consultarlos. Se construye con **funciones puras** y **funciones de orden superior**.

- **Cómo se sigue:** en cada paso se **copia** el código, se **ejecuta**, se **compara** la salida con la que aparece aquí y se lee *¿Qué pasó?*. Casi todos los pasos terminan con un **Pruebe**: un cambio pequeño que rompe algo a propósito para ver por qué el código está escrito así. Después de cada Pruebe, se deja el código como estaba.
- **Al final** queda un `persistencia.py` y un `consultas.py` que se llevan a cualquier proyecto cambiando el registro de ejemplo por el propio *(paso 9)*.
- **El ejemplo:** una bitácora de eventos `usuario | acción | hora`, como la de un sistema que registra quién entra y quién sale.

## Antes de empezar

- Python 3.10 o superior: `python --version` *(en Windows, `py --version`)*.
- Crear una carpeta vacía, `persistencia-guia/`, y abrir una terminal **dentro** de ella. Todos los archivos de la guía van ahí.
- Ejecutar cada script con `python paso_N.py` *(en Windows, `py paso_N.py`)*.

## Tres ideas que se van a ver funcionando

- **Función pura:** con el mismo argumento devuelve siempre el mismo resultado y no cambia nada fuera de sí misma.
- **Efecto:** todo lo que una función hace además de devolver un valor. Abrir o escribir un archivo, imprimir, leer la hora, modificar una variable global o una lista que recibió.
- **Función de orden superior:** recibe una función como argumento o devuelve una función. `map`, `filter`, `sorted(key=...)` y `threading.Thread(target=...)` lo son.

**La regla de esta guía:** los efectos se concentran en unas pocas funciones del **borde** (las que abren el archivo o imprimen), y todo lo demás es puro.

---

## Paso 1 · El punto de partida: guardar sin cuidado

**Copie** en `antes.py`:

```python
eventos = []


def registrar(usuario, accion):
    eventos.append((usuario, accion))
    with open("antes.log", "a", encoding="utf-8") as archivo:
        for usuario_guardado, accion_guardada in eventos:
            archivo.write(f"{usuario_guardado}|{accion_guardada}\n")
    print(f"Registrado: {usuario} {accion}")
    return len(eventos)


print(registrar("ana", "entrar"))
print(registrar("ana", "entrar"))

with open("antes.log", encoding="utf-8") as archivo:
    print("líneas en antes.log:", sum(1 for _ in archivo))
```

**Ejecute** `python antes.py`:

```
Registrado: ana entrar
1
Registrado: ana entrar
2
líneas en antes.log: 3
```

**¿Qué pasó?**

- **La misma llamada, `registrar("ana", "entrar")`, devolvió `1` y luego `2`.** El resultado depende de la lista global `eventos`, no solo de los argumentos.
- **Se registraron dos eventos, pero el archivo tiene tres líneas.** Cada llamada vuelve a escribir *toda* la lista en modo `"a"`, así que el primer evento quedó duplicado.
- **Una sola función hace cuatro cosas:** modifica una global, abre un archivo, escribe e imprime. Ninguna de ellas se puede probar por separado.
- **Ejecútelo otra vez:** ahora el archivo tiene 6 líneas. La lista global vuelve a empezar vacía, pero el archivo conserva lo anterior.

Los pasos siguientes separan esas cuatro cosas.

---

## Paso 2 · Un registro inmutable y una función pura que lo convierte en texto

**Copie** en `persistencia.py`. Este encabezado ya trae todos los `import` de la guía; algunos se usan más adelante:

```python
import json
import queue
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime
from typing import NamedTuple


class Evento(NamedTuple):
    usuario: str
    accion: str
    timestamp: datetime


def a_linea(evento: Evento) -> str:
    return json.dumps(
        {
            "usuario": evento.usuario,
            "accion": evento.accion,
            "timestamp": evento.timestamp.isoformat(timespec="seconds"),
        },
        ensure_ascii=False,
    )
```

**Copie** en `paso_2.py`:

```python
from datetime import datetime

from persistencia import Evento, a_linea

evento = Evento("sofía", "entrar", datetime(2026, 10, 20, 8, 30))

print(a_linea(evento))
print("¿misma línea las dos veces?", a_linea(evento) == a_linea(evento))

otro = evento._replace(accion="salir")
print(otro)
print(evento)
```

**Ejecute** `python paso_2.py`:

```
{"usuario": "sofía", "accion": "entrar", "timestamp": "2026-10-20T08:30:00"}
¿misma línea las dos veces? True
Evento(usuario='sofía', accion='salir', timestamp=datetime.datetime(2026, 10, 20, 8, 30))
Evento(usuario='sofía', accion='entrar', timestamp=datetime.datetime(2026, 10, 20, 8, 30))
```

**¿Qué pasó?**

- **`Evento` es un `NamedTuple`:** una tupla con nombres de campo. Es **inmutable**, así que nadie puede cambiar un evento después de crearlo.
- **`_replace` no modificó `evento`:** devolvió **otro** evento con un campo distinto. El original sigue con `accion='entrar'`.
- **`a_linea` es pura:** no abre archivos, no imprime y no lee la hora. La hora viaja **dentro** del evento. Por eso dos llamadas dan exactamente lo mismo.
- **Cada evento es una línea de JSON.** El formato se llama *JSON Lines*: un objeto por línea, fácil de agregar al final y de leer línea por línea.

**Pruebe:**

1. En `paso_2.py`, agregue al final `evento.accion = "salir"` y ejecute. Python responde `AttributeError: can't set attribute`: el registro no se deja cambiar. Después borre esa línea.
2. En `persistencia.py`, borre la línea `ensure_ascii=False,` y ejecute. Aparece `"sofía"`: sin ese parámetro las tildes se guardan como códigos. Vuelva a ponerla.

---

## Paso 3 · Escribir en el borde, pasando la función como argumento

**Copie** en `datos_prueba.py`. Son los datos de ejemplo de los pasos siguientes:

```python
from datetime import datetime

from persistencia import Evento

EVENTOS = (
    Evento("ana", "entrar", datetime(2026, 10, 20, 8, 0)),
    Evento("luis", "entrar", datetime(2026, 10, 20, 8, 5)),
    Evento("ana", "salir", datetime(2026, 10, 20, 9, 15)),
    Evento("sofía", "entrar", datetime(2026, 10, 20, 9, 20)),
)
```

**Agregue al final** de `persistencia.py`:

```python
def guardar(ruta: str, eventos: Iterable[Evento], serializar: Callable[[Evento], str]) -> None:
    with open(ruta, "a", encoding="utf-8") as archivo:
        for evento in eventos:
            archivo.write(serializar(evento) + "\n")
```

**Copie** en `paso_3.py`:

```python
from datos_prueba import EVENTOS
from persistencia import a_linea, guardar

guardar("eventos.log", EVENTOS, a_linea)

with open("eventos.log", encoding="utf-8") as archivo:
    print(archivo.read(), end="")
```

**Ejecute** `python paso_3.py`:

```
{"usuario": "ana", "accion": "entrar", "timestamp": "2026-10-20T08:00:00"}
{"usuario": "luis", "accion": "entrar", "timestamp": "2026-10-20T08:05:00"}
{"usuario": "ana", "accion": "salir", "timestamp": "2026-10-20T09:15:00"}
{"usuario": "sofía", "accion": "entrar", "timestamp": "2026-10-20T09:20:00"}
```

**¿Qué pasó?**

- **`guardar` es el borde:** es la única función que abre el archivo para escribir. El efecto quedó en un solo lugar.
- **`guardar` recibe una función, `serializar`.** No sabe nada de JSON: solo llama a lo que le pasen. Es una **función de orden superior**.
- **`a_linea` se pasó sin paréntesis:** `a_linea` es la función; `a_linea(evento)` sería su resultado.
- **Ejecútelo otra vez:** aparecen 8 líneas. El modo `"a"` (*append*) agrega al final y no borra lo que había. Para una bitácora eso es lo correcto.

**Pruebe:** guardar en otro formato **sin tocar `guardar`**. Agregue al final de `paso_3.py`:

```python
from persistencia import Evento


def a_csv(evento: Evento) -> str:
    return f"{evento.usuario},{evento.accion},{evento.timestamp:%Y-%m-%d %H:%M}"


guardar("eventos.csv", EVENTOS, a_csv)
```

Abra `eventos.csv`: tiene las mismas cuatro filas en CSV (`ana,entrar,2026-10-20 08:00`). Cambiar de formato fue cambiar el argumento, no la función.

---

## Paso 4 · Volver de texto a registro sin romperse

**Agregue al final** de `persistencia.py`:

```python
def desde_linea(linea: str) -> Evento | None:
    try:
        datos = json.loads(linea)
        return Evento(
            usuario=datos["usuario"],
            accion=datos["accion"],
            timestamp=datetime.fromisoformat(datos["timestamp"]),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
```

**Copie** en `paso_4.py`:

```python
from persistencia import desde_linea

buena = '{"usuario": "ana", "accion": "entrar", "timestamp": "2026-10-20T08:00:00"}'
print(desde_linea(buena))

malas = [
    '{"usuario": "ana"',
    '{"usuario": "ana"}',
    '"hola"',
    '{"usuario": "ana", "accion": "entrar", "timestamp": "ayer"}',
]
for linea in malas:
    print(linea, "->", desde_linea(linea))
```

**Ejecute** `python paso_4.py`:

```
Evento(usuario='ana', accion='entrar', timestamp=datetime.datetime(2026, 10, 20, 8, 0))
{"usuario": "ana" -> None
{"usuario": "ana"} -> None
"hola" -> None
{"usuario": "ana", "accion": "entrar", "timestamp": "ayer"} -> None
```

**¿Qué pasó?**

- **La línea buena volvió a ser un `Evento`,** con la hora como `datetime` y no como texto.
- **Cada línea mala devolvió `None` en lugar de detener el programa.** Cada una falla por una razón distinta:

| Línea | Error que se atrapa | Por qué |
| --- | --- | --- |
| `{"usuario": "ana"` | `JSONDecodeError` | JSON incompleto |
| `{"usuario": "ana"}` | `KeyError` | Faltan campos |
| `"hola"` | `TypeError` | Es JSON válido, pero no es un objeto |
| `"timestamp": "ayer"` | `ValueError` | La hora no tiene formato ISO |

- **Sigue siendo pura:** no imprime el error ni escribe en ningún lado. Quien la llama decide qué hacer con un `None`.

**Pruebe:** en `desde_linea`, deje solo lo que hay dentro del `try` (quite `try:`, el `except` y la sangría) y ejecute. El programa se detiene en la primera línea mala con `json.decoder.JSONDecodeError: Expecting ',' delimiter`. Un archivo con una sola línea dañada dejaría todo el resto sin leer. Vuelva a dejarlo como estaba.

---

## Paso 5 · De líneas a eventos con `map` y `filter`

**Agregue al final** de `persistencia.py`:

```python
def eventos(lineas: Iterable[str]) -> Iterator[Evento]:
    return filter(None, map(desde_linea, lineas))
```

**Copie** en `paso_5.py`:

```python
from persistencia import eventos

lineas = [
    '{"usuario": "ana", "accion": "entrar", "timestamp": "2026-10-20T08:00:00"}',
    "esta línea está dañada",
    '{"usuario": "luis", "accion": "entrar", "timestamp": "2026-10-20T08:05:00"}',
]

flujo = eventos(lineas)
print(flujo)
print("todavía no se ha procesado ninguna línea")

for evento in flujo:
    print(evento.usuario, evento.accion)

print("segunda vuelta:", list(flujo))
```

**Ejecute** `python paso_5.py` *(el número `0x...` cambia en cada máquina)*:

```
<filter object at 0x7fb8beea52a0>
todavía no se ha procesado ninguna línea
ana entrar
luis entrar
segunda vuelta: []
```

**¿Qué pasó?**

- **`map(desde_linea, lineas)`** aplica `desde_linea` a cada línea. **`filter(None, ...)`** deja pasar solo lo que no es `None`, así que la línea dañada desaparece.
- **Las dos son de orden superior** y aquí reciben una función que ya existe, sin `lambda`.
- **`print(flujo)` no mostró eventos, sino `<filter object ...>`.** `map` y `filter` son **perezosos**: no procesan nada hasta que alguien pide el siguiente elemento.
- **La segunda vuelta salió vacía.** Un flujo perezoso se recorre **una sola vez**. Si se necesita recorrerlo de nuevo, se vuelve a crear o se guarda en una tupla.
- **`eventos` recibe líneas, no un nombre de archivo.** Por eso se pudo probar con una lista, sin crear ningún archivo.

**Pruebe:** para **ver** la pereza, agregue esta línea como primera instrucción de `desde_linea`, antes del `try`:

```python
    print(f"procesando: {linea[:20]}")
```

Ejecute `python paso_5.py`:

```
<filter object at 0x7f2f89bdd8d0>
todavía no se ha procesado ninguna línea
procesando: {"usuario": "ana", "
ana entrar
procesando: esta línea está daña
procesando: {"usuario": "luis", 
luis entrar
segunda vuelta: []
```

Cada línea se procesa **justo cuando el `for` la pide**, no antes. **Después borre ese `print`:** con él, `desde_linea` deja de ser pura.

---

## Paso 6 · Leer el archivo con un generador

**Agregue al final** de `persistencia.py`:

```python
def leer(ruta: str) -> Iterator[Evento]:
    with open(ruta, encoding="utf-8") as archivo:
        yield from eventos(archivo)
```

**Copie** en `paso_6.py`:

```python
import os

from datos_prueba import EVENTOS
from persistencia import a_linea, guardar, leer

RUTA = "eventos.log"
if os.path.exists(RUTA):
    os.remove(RUTA)

guardar(RUTA, EVENTOS, a_linea)
with open(RUTA, "a", encoding="utf-8") as archivo:
    archivo.write("esta línea está dañada\n")

lector = leer(RUTA)
print(lector)
print(next(lector))
print(next(lector))
print("quedan:", sum(1 for _ in lector))
```

**Ejecute** `python paso_6.py`:

```
<generator object leer at 0x7f2f947e0b80>
Evento(usuario='ana', accion='entrar', timestamp=datetime.datetime(2026, 10, 20, 8, 0))
Evento(usuario='luis', accion='entrar', timestamp=datetime.datetime(2026, 10, 20, 8, 5))
quedan: 2
```

**¿Qué pasó?**

- **`leer` es un generador** (tiene `yield`). Al llamarlo no lee nada: devuelve un objeto que entrega un evento cada vez que se le pide con `next` o con un `for`.
- **El archivo tiene 5 líneas:** 4 eventos y 1 dañada. Se pidieron 2 con `next` y quedaban 2 eventos válidos. La línea dañada se omitió sola, gracias al paso 5.
- **`leer` es el borde de la lectura:** la única función que abre el archivo para leer. Por dentro reutiliza `eventos`, que es pura.
- **El archivo se lee línea por línea, nunca completo.** La memoria que usa no depende del tamaño del archivo: 4 líneas o 4 millones ocupan lo mismo. Por eso no se usa `archivo.readlines()` ni `list(...)`.

---

## Paso 7 · Consultas puras

**Copie** en un archivo nuevo, `consultas.py`:

```python
from collections import Counter
from collections.abc import Iterable
from functools import partial, reduce
from operator import attrgetter

from persistencia import Evento


def es_de(usuario: str, evento: Evento) -> bool:
    return evento.usuario == usuario


def de_usuario(usuario: str, eventos: Iterable[Evento]) -> tuple[Evento, ...]:
    return tuple(filter(partial(es_de, usuario), eventos))


def usuarios(eventos: Iterable[Evento]) -> list[str]:
    return sorted(set(map(attrgetter("usuario"), eventos)))


def por_accion(eventos: Iterable[Evento]) -> Counter[str]:
    return Counter(map(attrgetter("accion"), eventos))


def _quedarse_con_el_ultimo(acc: dict[str, str], evento: Evento) -> dict[str, str]:
    return {**acc, evento.usuario: evento.accion}


def estado_actual(eventos: Iterable[Evento]) -> dict[str, str]:
    return reduce(_quedarse_con_el_ultimo, eventos, {})


def recientes_primero(eventos: Iterable[Evento]) -> list[Evento]:
    return sorted(eventos, key=lambda evento: evento.timestamp, reverse=True)


def horas(eventos: Iterable[Evento]) -> list[str]:
    return [f"{evento.usuario} {evento.timestamp:%H:%M}" for evento in eventos]
```

**Copie** en `paso_7.py`:

```python
from consultas import de_usuario, estado_actual, horas, por_accion, recientes_primero, usuarios
from datos_prueba import EVENTOS

print("de ana:     ", horas(de_usuario("ana", EVENTOS)))
print("usuarios:   ", usuarios(EVENTOS))
print("por acción: ", por_accion(EVENTOS))
print("estado:     ", estado_actual(EVENTOS))
print("recientes:  ", horas(recientes_primero(EVENTOS)))
print("original:   ", horas(EVENTOS))
print("¿mismo resultado?", estado_actual(EVENTOS) == estado_actual(EVENTOS))
```

**Ejecute** `python paso_7.py`:

```
de ana:      ['ana 08:00', 'ana 09:15']
usuarios:    ['ana', 'luis', 'sofía']
por acción:  Counter({'entrar': 3, 'salir': 1})
estado:      {'ana': 'salir', 'luis': 'entrar', 'sofía': 'entrar'}
recientes:   ['sofía 09:20', 'ana 09:15', 'luis 08:05', 'ana 08:00']
original:    ['ana 08:00', 'luis 08:05', 'ana 09:15', 'sofía 09:20']
¿mismo resultado? True
```

**¿Qué pasó?** Cada consulta usa una herramienta distinta, elegida por lo que hace:

| Consulta | Herramienta | Por qué esa |
| --- | --- | --- |
| `de_usuario` | `filter` + `partial` | `partial(es_de, "ana")` **crea una función nueva** con el usuario fijado, y `filter` la usa como condición |
| `usuarios`, `por_accion` | `map` + `attrgetter` | Saca un campo de cada evento sin escribir una `lambda`; `Counter` cuenta |
| `estado_actual` | `reduce` | El acumulado es un diccionario que se va reemplazando, no una suma. `{**acc, ...}` crea un diccionario nuevo en cada paso: no modifica el anterior |
| `recientes_primero` | `sorted` con `key=lambda` | Una `lambda` corta, usada en el único lugar donde se necesita |
| `horas` | comprehension | Transformar cada elemento con un formato: aquí se lee mejor que `map` con `lambda` |

- **`original` sigue en el orden de entrada.** `sorted` devolvió una lista **nueva**; ninguna consulta modificó `EVENTOS`.
- **Todas son puras:** reciben los eventos y devuelven un resultado. No abren el archivo, así que funcionan igual con `EVENTOS` o con `leer("eventos.log")`.

**Pruebe:** la diferencia entre `sorted` y `.sort()`. Agregue al final de `paso_7.py`:

```python
lista = list(EVENTOS)
print(lista.sort(key=lambda evento: evento.usuario, reverse=True))
print(horas(lista))
```

Salida:

```
None
['sofía 09:20', 'luis 08:05', 'ana 08:00', 'ana 09:15']
```

`.sort()` devuelve `None` y **cambia la lista que recibe**: tiene un efecto. `sorted(...)` deja el original intacto y devuelve una lista nueva. Dentro de una consulta pura se usa `sorted`.

---

## Paso 8 · Varios hilos, un solo escritor

Cuando varios hilos producen eventos al mismo tiempo (por ejemplo, un servidor con un hilo por cliente), **no** se abre el archivo desde cada hilo. Los hilos ponen los eventos en una **cola**, y **un solo hilo** los saca y los escribe.

**Agregue al final** de `persistencia.py`:

```python
def escritor(cola: "queue.Queue[Evento | None]", ruta: str, serializar: Callable[[Evento], str]) -> None:
    with open(ruta, "a", encoding="utf-8") as archivo:
        while (evento := cola.get()) is not None:
            archivo.write(serializar(evento) + "\n")
```

**Copie** en `paso_8.py`:

```python
import os
import queue
import threading
import time
from datetime import datetime

from persistencia import Evento, a_linea, escritor

RUTA = "concurrente.log"
if os.path.exists(RUTA):
    os.remove(RUTA)

cola: "queue.Queue[Evento | None]" = queue.Queue()
hilo_escritor = threading.Thread(target=escritor, args=(cola, RUTA, a_linea))
hilo_escritor.start()


def productor(usuario: str) -> None:
    for i in range(1000):
        cola.put(Evento(usuario, f"accion-{i}", datetime(2026, 10, 20, 8, 0)))
        time.sleep(0.001)


productores = [threading.Thread(target=productor, args=(nombre,)) for nombre in ("ana", "luis", "sofía")]
for hilo in productores:
    hilo.start()
for hilo in productores:
    hilo.join()

cola.put(None)
hilo_escritor.join()

with open(RUTA, encoding="utf-8") as archivo:
    print("líneas escritas:", sum(1 for _ in archivo))
```

**Ejecute** `python paso_8.py` *(tarda alrededor de un segundo)*:

```
líneas escritas: 3000
```

**¿Qué pasó?**

- **Tres hilos produjeron 1000 eventos cada uno y no se perdió ninguno.** La `queue.Queue` ya está protegida para usarse desde varios hilos: no hace falta un `Lock`.
- **Solo `escritor` abre el archivo.** Es el mismo borde del paso 3, ahora en su propio hilo, y también recibe `serializar` como argumento.
- **`None` es el centinela:** significa «no llegan más eventos». El escritor sale del `while`, el `with` cierra el archivo y el hilo termina.
- **El orden importa:** primero se espera a los productores (`join`), después se pone el centinela y al final se espera al escritor.
- **`time.sleep(0.001)`** solo simula que los eventos llegan de a poco, como en un programa real.

**Pruebe**, un cambio a la vez, y deje el archivo como estaba después de cada uno:

1. **El centinela antes de tiempo.** Mueva `cola.put(None)` para que quede justo después del `for` que hace `hilo.start()`. Salida: `líneas escritas: 3`. El escritor recibió el `None` cuando los productores apenas empezaban, y todo lo que se puso después quedó en la cola sin escribir.
2. **Sin centinela.** Borre `cola.put(None)` y `hilo_escritor.join()`. El programa imprime un número menor que 3000 y **no termina nunca**: el escritor se queda esperando en `cola.get()`. Deténgalo con `Ctrl+C`.
3. **Sin centinela y con `daemon=True`.** Además del cambio anterior, cree el hilo con `threading.Thread(target=escritor, args=(cola, RUTA, a_linea), daemon=True)`. Ahora el programa termina, pero el archivo queda incompleto: en una prueba quedaron 1536 líneas de 3000, y el número cambia en cada máquina. Un hilo `daemon` muere cuando termina el programa, sin vaciar la cola ni cerrar el archivo. **Por eso el escritor no es `daemon` y se cierra con centinela y `join`.**

---

## Paso 9 · Lo que quedó y cómo llevarlo a su proyecto

**Lo que hay en la carpeta:**

```bash
persistencia-guia/
├── persistencia.py   # Evento, a_linea, guardar, desde_linea, eventos, leer, escritor
├── consultas.py      # consultas puras sobre cualquier Iterable[Evento]
├── datos_prueba.py   # eventos de ejemplo
├── antes.py          # la versión del paso 1, para comparar
└── paso_2.py … paso_8.py
```

**Qué es cada función:**

| Función | Tipo | Qué hace |
| --- | --- | --- |
| `a_linea`, `desde_linea` | Pura | Convierte entre registro y texto |
| `eventos` | Pura, de orden superior por dentro | De líneas a registros, omitiendo las dañadas |
| `consultas.py` | Puras | Responden preguntas sobre los registros |
| `guardar` | Borde, de orden superior | Escribe; recibe la función que serializa |
| `leer` | Borde, generador | Lee línea por línea |
| `escritor` | Borde, de orden superior, en su propio hilo | Escribe desde una cola cuando hay varios hilos |

**Para llevarlo a su proyecto:**

1. **Cambie `Evento` por su registro.** Un `NamedTuple` con los campos que su programa guarda: un pedido, un mensaje, una lectura de sensor.
2. **Ajuste `a_linea` y `desde_linea`** a esos campos. Las fechas viajan como texto ISO (`isoformat` / `fromisoformat`), y en `desde_linea` use `datos.get("campo")` para los campos opcionales.
3. **Si su programa tiene un solo hilo**, use `guardar` y `leer`. **Si tiene varios**, use `escritor` con una cola y un único hilo que no sea `daemon`.
4. **Escriba sus consultas en `consultas.py`** como funciones que reciben un `Iterable` de registros y devuelven un valor. Que no abran archivos ni impriman.
5. **Imprima en un solo lugar**, en el `main` de su programa, con lo que devuelven las consultas.
6. **Copie el estilo de los `paso_N.py` como pruebas:** cada función pura se comprueba llamándola con datos fijos, sin archivo y sin hilos.

**Reglas que no se rompen:**

- Una función pura no abre archivos, no imprime, no lee la hora y no modifica lo que recibe (`.append`, `.sort()`).
- No hay listas globales que se modifiquen.
- Solo un hilo escribe el archivo.
- No se lee el archivo completo con `readlines()` o `list(...)` si se puede recorrer línea por línea.
- JSON y no `pickle` para guardar: un archivo `pickle` alterado puede ejecutar código al cargarse.