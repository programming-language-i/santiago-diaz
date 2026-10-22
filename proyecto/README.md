# Sistema de Mensajería Interna para Centro de Distribución

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Type Checked with mypy](https://img.shields.io/badge/mypy-checked-green.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Sistema de mensajería interna y auditoría operativa para centros de distribución y bodegas logísticas. Implementado exclusivamente sobre la **biblioteca estándar de Python** (sin dependencias externas en producción), diseñado bajo principios de **Clean Code**, alta concurrencia multihilo, framing estricto por longitud sobre TCP, monitoreo de disponibilidad por datagramas UDP y procesamiento analítico de bitácoras mediante **programación funcional**.

---

## 1. Problemática Operativa y Solución

En una operación logística que atiende en tres turnos a ~40 operarios (recepción, alistamiento, despacho y supervisión), el uso de radios y grupos de WhatsApp genera fallas críticas:
1. **Falta de registro:** Pérdida de trazabilidad de avisos en despachos incompletos o pedidos extraviados.
2. **Fuga de datos de clientes:** La política de seguridad corporativa prohíbe exponer información a servidores externos/nube.
3. **Desconocimiento de disponibilidad:** Asignación de tareas a operarios ausentes o inactivos.
4. **Falta de datos para la toma de decisiones:** Desconocimiento de las horas pico e incidencias recurrentes.
5. **Saturación y ruido:** Instrucciones operativas específicas perdidas en canales globales.

### Solución Implementada
- **Red Local Cerrada:** Servidor TCP en puerto `8000` y UDP en puerto `8001`, sin salida a internet ni dependencias en la nube.
- **Identidad Única e Insuplantable:** Cada operario ingresa con identidad validada; el servidor sella el emisor, ID único y timestamp UTC ISO-8601.
- **Canales Fijos por Área y Mensajería Privada:** Canales fijos (`#general`, `#recepcion`, `#alistamiento`, `#despacho`) y comunicación directa persona a persona.
- **Bitácora Auditable Persistente:** Cada mensaje aceptado se escribe en disco en formato JSON Lines con `flush()` y `fsync()` inmediatos (tolerante a cortes eléctricos).
- **Control de Disponibilidad por Heartbeat UDP:** Reporte periódico desde cada estación; si un puesto supera 15 segundos sin reportar, se clasifica automáticamente como `INACTIVO`.
- **Reporte Operativo Funcional en Streaming ($O(1)$ de Memoria):** Análisis de más de 100.000 mensajes mensuales (~24 MB) mediante generadores perezosos, `map`, `filter` y `reduce` en menos de 2 segundos sin saturar la memoria RAM.

---

## 2. Arquitectura y Estructura de la Carpeta

El proyecto está estructurado de manera modular y desacoplada (Clean Code) dentro de la carpeta `proyecto/`:

```
proyecto/
├── mensajeria/                     # Paquete principal del sistema
│   ├── __init__.py                 # Exportación de clases públicas y versión
│   ├── config.py                   # Constantes de red, canales fijos y timeouts
│   ├── utilidades.py               # Funciones puras de timestamps, tokens y stopwords
│   ├── protocolo.py                # Framing TCP (prefijo de 4 bytes big-endian) y datagramas UDP
│   ├── bitacora.py                 # Persistencia atómica en JSONL con fsync y lectura en streaming
│   ├── estado.py                   # Registro concurrente de usuarios, membresías y disponibilidad
│   ├── servidor.py                 # Servidor multihilo TCP (8000) + UDP (8001) + monitor
│   ├── cliente.py                  # Cliente interactivo de estación con hilos de recepción y heartbeat
│   └── reporte.py                  # Análisis funcional (map/filter/reduce) con O(1) de memoria
├── scripts/                        # Scripts ejecutables desde terminal
│   ├── iniciar_servidor.py         # Punto de entrada para el servidor
│   ├── iniciar_cliente.py          # Punto de entrada para la estación de trabajo
│   ├── generar_reporte.py          # Generador de reportes ejecutables
│   └── simular_bitacora.py         # Simulador de 1 mes de operación (~100.000 mensajes)
├── tests/                          # Suite completa de pruebas automatizadas
│   ├── __init__.py
│   ├── test_protocolo.py           # Pruebas de framing, fragmentación y resiliencia
│   ├── test_bitacora.py            # Pruebas de persistencia y concurrencia multihilo
│   ├── test_estado.py              # Pruebas de identidad única y verificación de disponibilidad
│   ├── test_reporte.py             # Pruebas de transformaciones y agregaciones funcionales
│   └── test_integracion.py         # Pruebas E2E de servidor, múltiples clientes y tolerancia a fallas
├── mypy.ini                        # Configuración estricta de verificación de tipos
├── .gitignore                      # Exclusiones de Git locales del proyecto
└── README.md                       # Documentación técnica del proyecto
```

---

## 3. Matriz de Cumplimiento de Requisitos

| ID | Requerimiento | Hito | Estado | Módulo / Implementación |
|:---:|:---|:---:|:---:|:---|
| **01** | **Conexión con identidad:** Cada persona se conecta con su nombre; no puede haber dos sesiones con el mismo nombre. | 1 | **Cumplido** | [estado.py](mensajeria/estado.py), [servidor.py](mensajeria/servidor.py) |
| **02** | **Canal común:** Lo que una persona escribe llega a todas las demás conectadas, completo y sin mezclarse. Canal `#general`. | 1 | **Cumplido** | [servidor.py](mensajeria/servidor.py), [cliente.py](mensajeria/cliente.py) |
| **03** | **Varias estaciones a la vez:** El servidor atiende al menos tres clientes simultáneos sin límite fijo. | 1 | **Cumplido** | [servidor.py](mensajeria/servidor.py) (Multihilo) |
| **04** | **Tolerancia a fallas de una estación:** Si un equipo se apaga o pierde la red, el servidor y las demás siguen funcionando. | 1 | **Cumplido** | [servidor.py](mensajeria/servidor.py), [test_integracion.py](tests/test_integracion.py) |
| **05** | **Registro de conectados:** El servidor sabe en todo momento quién está conectado, su estado y última actividad. | 1 y 2 | **Cumplido** | [estado.py](mensajeria/estado.py) (`RegistroConectados`) |
| **06** | **Autoría no suplantable:** El emisor y la hora de cada mensaje los pone el servidor, nunca el cliente. | 2 | **Cumplido** | [servidor.py](mensajeria/servidor.py) (Inyección de emisor, ID y timestamp UTC) |
| **07** | **Bitácora auditable:** Cada mensaje aceptado queda guardado en disco; apagar el servidor no pierde ninguno. | 2 | **Cumplido** | [bitacora.py](mensajeria/bitacora.py) (`flush()` y `os.fsync()`) |
| **08** | **Disponibilidad:** Cada estación reporta activa (UDP 8001); >15 segundos sin reportar aparece como inactivo. | 2 | **Cumplido** | [cliente.py](mensajeria/cliente.py), [servidor.py](mensajeria/servidor.py) |
| **09** | **Reporte de operación:** Ranking de emisores, mensajes por hora del día (0-23) y palabras más frecuentes. | 3 | **Cumplido** | [reporte.py](mensajeria/reporte.py) |
| **10** | **Reporte sobre un mes (~100.000 msgs):** Procesamiento en streaming sin incremento lineal de memoria RAM. | 3 | **Cumplido** | [reporte.py](mensajeria/reporte.py) ($O(1)$ memoria adicional) |
| **11** | **Canales por área:** Cuatro canales fijos (`#general`, `#recepcion`, `#alistamiento`, `#despacho`). | 2 | **Cumplido** | [estado.py](mensajeria/estado.py), [servidor.py](mensajeria/servidor.py) |
| **12** | **Mensajes privados:** Comunicación directa entre dos operarios conectadas con entrega exclusiva y auditoría. | 2 | **Cumplido** | [servidor.py](mensajeria/servidor.py), [cliente.py](mensajeria/cliente.py) |

---

## 4. Requerimientos de Evaluación Técnica

1. **Solo Red Local:** Servidor TCP en puerto `8000` y UDP en puerto `8001`. En desarrollo opera sobre `127.0.0.1`.
2. **Biblioteca Estándar:** 100% Python estándar (`socket`, `threading`, `json`, `struct`, `functools`, `collections`, `dataclasses`, `pathlib`).
3. **JSON y UTF-8 (Sin Pickle):** Toda serialización usa estrictamente JSON UTF-8 para prevenir vulnerabilidades de ejecución arbitraria de código (OWASP A08).
4. **Framing por Prefijo de Longitud y `SO_REUSEADDR`:** Cada trama TCP viaja precedida por 4 bytes big-endian (`!I`) indicando la longitud exacta en bytes. Se reutiliza la dirección con `SO_REUSEADDR` evitando puertos bloqueados al reiniciar el servidor.
5. **Entrada Inválida no Tumba el Servidor:** Si un cliente envía un JSON corrupto, tramas partidas o desconexiones abruptas, el servidor descarta la trama o limpia la sesión sin detener la atención a los demás clientes.
6. **Mantenibilidad y Type Hints:** Código estructurado en clases con responsabilidades únicas, type hints completos en todas las funciones y clases, y **`mypy mensajeria` ejecutando con 0 errores**.

---

## 5. Guía de Ejecución

> Se recomienda abrir la terminal y ubicarse dentro de la carpeta `proyecto`:
> ```bash
> cd proyecto
> ```

### 5.1. Iniciar el Servidor
En una terminal:
```bash
python scripts/iniciar_servidor.py
```
*Opciones disponibles:*
- `--host`: Dirección IP de escucha (por defecto `127.0.0.1`).
- `--tcp`: Puerto TCP (por defecto `8000`).
- `--udp`: Puerto UDP (por defecto `8001`).
- `--bitacora`: Ruta del archivo de persistencia (por defecto `bitacora_mensajes.jsonl`).

### 5.2. Conectar Estaciones de Trabajo (Clientes)
Abra una o varias terminales para simular diferentes puestos de trabajo:
```bash
# Estación 1: Supervisor
python scripts/iniciar_cliente.py -u supervisor_turno1

# Estación 2: Recepción
python scripts/iniciar_cliente.py -u carlos_recepcion

# Estación 3: Alistamiento
python scripts/iniciar_cliente.py -u ana_alistamiento
```

#### Comandos Disponibles en la Consola del Cliente:
- **Escribir mensaje normal:** Escriba cualquier texto y presione Enter; se enviará al canal activo (por defecto `#general`).
- `/canal <#canal>`: Cambia el canal activo para redactar mensajes directamente.
- `/unir <#canal>`: Se une a un canal de área (`#recepcion`, `#alistamiento`, `#despacho`).
- `/salir_canal <#canal>`: Abandona un canal de área (no permite salir del canal común `#general`).
- `/canales`: Muestra los canales existentes y las membresías de la estación.
- `/usuarios`: Muestra los operarios conectados, su estado (`ACTIVO` / `INACTIVO`), su última actividad y sus canales.
- `/msg <usuario> <mensaje>`: Envía un mensaje privado exclusivo a otro operario.
- `/ayuda`: Muestra la lista de comandos.
- `/salir`: Cierra la sesión y desconecta la estación de forma segura.

### 5.3. Generar el Reporte Operativo (Hito 3)
Para procesar la bitácora auditable y generar el reporte analítico en consola o exportarlo a un archivo:
```bash
python scripts/generar_reporte.py --bitacora bitacora_mensajes.jsonl
```
*Opcional: exportar a archivo de texto:*
```bash
python scripts/generar_reporte.py --bitacora bitacora_mensajes.jsonl --salida reporte_operacion.txt
```

### 5.4. Simulación de Carga (~100.000 Mensajes / 1 Mes de Operación)
Para validar el Requisito 10 con una bitácora masiva de 100.000 mensajes generados en los 3 turnos:
```bash
# Generar bitácora simulada de 100.000 mensajes
python scripts/simular_bitacora.py --cantidad 100000 --salida bitacora_simulada.jsonl

# Ejecutar el reporte funcional en streaming sobre la bitácora de 100.000 mensajes
python scripts/generar_reporte.py --bitacora bitacora_simulada.jsonl
```
*El procesamiento de los 100.000 registros toma aproximadamente 1.5 segundos con un consumo de memoria plano constante ($O(1)$).*

---

## 6. Pruebas Automatizadas y Verificación de Tipos

### 6.1. Ejecutar la Suite de Pruebas Unitaria y de Integración
Ejecute todas las pruebas con el ejecutor nativo de Python (desde la carpeta `proyecto`):
```bash
python -m unittest discover -s tests -v
```
Se ejecutan 22 pruebas automatizadas cubriendo:
- Framing por prefijo de 4 bytes y fragmentación de TCP.
- Persistencia en disco, concurrencia multihilo y llamadas a `fsync()`.
- Unicidad de usuarios y rechazo de nombres duplicados.
- Reglas de canales fijos y membresías dinámicas.
- Verificación de inactividad a los 15 segundos y reactivación mediante heartbeats UDP.
- Autoría no suplantable y marcas temporales UTC del servidor.
- Tolerancia a fallas por desconexión abrupta o tramas con JSON corrupto.
- Pipelines funcionales de extracción, filtrado y reducción.

### 6.2. Verificación Estricta con mypy
Para validar que el código no contiene errores de tipado:
```bash
python -m mypy mensajeria
```
Salida esperada:
```
Success: no issues found in 9 source files
```
