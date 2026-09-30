# Primer Parcial

Lenguaje de Programación I: hilos, `join()`, GIL, herencia de `Thread`, daemon, procesos, `Lock`, condiciones de carrera y deadlock.

| Tramo | Qué | Dónde |
| --- | --- | --- |
| 1 | E1 y E2 | este repo, hasta la **hora límite del push** |
| 2 | Teoría | cuestionario de **Moodle** |

- **El cuestionario de Moodle se abre cuando termina el tiempo de código.** Varias preguntas del cuestionario son sobre el código de E1 y E2 que usted entregó en su repositorio. Téngalo abierto durante el tramo 2.
- **Internet:** solo para Moodle, GitHub y la documentación de Python ([docs.python.org](https://docs.python.org/3.14/)). Nada de IA ni chats.
- **Entrega:** por GitHub. Vea los pasos en el [README principal](../README.md). Haga commit y push al terminar cada ejercicio (mínimo 2 commits).

---

## Ejercicios

Cada ejercicio se califica así: **funciona 50 %**, **corrección técnica 30 %** y **claridad 20 %**. Un programa que no ejecuta se califica sobre el 50 %.

### E1 · `e1_sensores.py`

Complete los `TODO` de una estación meteorológica: un hilo por sensor, creado por herencia. Los requisitos y la salida exacta esperada están en el docstring del archivo.

### E2 · `e2_inventario.py`

Tiene el inventario de una tienda (100 unidades, 8 cajeros) con una condición de carrera. El archivo corre el experimento 10 veces. Corrija **solo la clase** y deje un comentario `# CORRECCIÓN: ...` que explique qué estaba mal. Está resuelto cuando las 10 corridas dicen:

```
quedan   0 unidades, vendidas 100
```
