"""Reporte analítico funcional sobre la bitácora (Hito 3).

Usa programación funcional: funciones puras, generadores perezosos,
map/filter/reduce para procesar >100k mensajes con O(1) memoria.
"""

from collections import Counter
from dataclasses import dataclass, field
import functools
from pathlib import Path
import sys
from typing import Any, Callable, Iterable, Iterator

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.bitacora import BitacoraAuditable
from mensajeria.config import ARCHIVO_BITACORA_POR_DEFECTO
from mensajeria.utilidades import extraer_hora_del_dia, tokenizar_palabras

TOP_EMISORES = 10
TOP_PALABRAS = 15


@dataclass(frozen=True)
class MetricasOperacion:
    """Acumulador inmutable de estadísticas operativas."""
    total_mensajes: int = 0
    conteo_emisores: Counter = field(default_factory=Counter)
    conteo_horas: tuple[int, ...] = field(default_factory=lambda: tuple([0] * 24))
    conteo_palabras: Counter = field(default_factory=Counter)
    conteo_canales: Counter = field(default_factory=Counter)


# --- Funciones puras de extracción (lambdas declarativas) ---
extraer_emisor = lambda m: str(m.get("emisor", "DESCONOCIDO")).strip()
extraer_hora = lambda m: extraer_hora_del_dia(str(m.get("timestamp", "")))
extraer_palabras = lambda m: tokenizar_palabras(str(m.get("texto", "")))
es_mensaje_valido = lambda m: bool(m.get("texto") and m.get("emisor"))


def extraer_canal(m: dict[str, Any]) -> str:
    """Extrae canal o etiqueta del mensaje."""
    if "canal" in m:
        return str(m["canal"])
    return "[PRIVADO]" if "destinatario" in m else "[SISTEMA]"


# Alias para compatibilidad con tests
extraer_palabras_mensaje = extraer_palabras


# --- Pipeline funcional de streaming ---
def filtrar_mensajes(it: Iterable[dict[str, Any]], pred: Callable[[dict[str, Any]], bool]) -> Iterator[dict[str, Any]]:
    """Filtrado perezoso declarativo."""
    return (m for m in it if pred(m))


def acumulador_reduccion(acc: MetricasOperacion, msg: dict[str, Any]) -> MetricasOperacion:
    """Paso reductor: incorpora un mensaje al acumulador sin mutarlo."""
    emisor, canal, hora = extraer_emisor(msg), extraer_canal(msg), extraer_hora(msg)
    palabras = extraer_palabras(msg)

    ne = Counter(acc.conteo_emisores); ne[emisor] += 1
    nc = Counter(acc.conteo_canales); nc[canal] += 1
    np = Counter(acc.conteo_palabras); np.update(palabras)
    horas = list(acc.conteo_horas)
    if 0 <= hora <= 23:
        horas[hora] += 1

    return MetricasOperacion(acc.total_mensajes + 1, ne, tuple(horas), np, nc)


def procesar_bitacora_stream(stream: Iterable[dict[str, Any]]) -> MetricasOperacion:
    """Procesa flujo de mensajes con filter + reduce (O(1) memoria adicional)."""
    return functools.reduce(acumulador_reduccion, filtrar_mensajes(stream, es_mensaje_valido), MetricasOperacion())


def generar_reporte_desde_archivo(ruta: str | Path = ARCHIVO_BITACORA_POR_DEFECTO) -> MetricasOperacion:
    """Lee bitácora en streaming y genera métricas."""
    return procesar_bitacora_stream(BitacoraAuditable(ruta).iterar_mensajes())


# --- Formateo del reporte ---
def generar_texto_reporte(m: MetricasOperacion, top_emisores_n: int = TOP_EMISORES, top_palabras_n: int = TOP_PALABRAS) -> str:
    """Genera informe formateado."""
    sep = "=" * 70
    lineas = [sep, "        REPORTE DE OPERACIÓN Y AUDITORÍA - CENTRO DE DISTRIBUCIÓN", sep,
              f"Total de mensajes analizados: {m.total_mensajes:,}", ""]

    # 1. Top emisores (declarativo: enumerate sobre most_common)
    lineas.append("--- 1. TOP EMISORES DE MENSAJES ---")
    emisores = m.conteo_emisores.most_common(top_emisores_n)
    if not emisores:
        lineas.append("  (Sin datos)")
    else:
        pct = lambda cant: (cant / m.total_mensajes * 100) if m.total_mensajes > 0 else 0
        lineas.extend(f"  {i:2d}. {e:<20} : {c:6,d} msgs ({pct(c):5.1f}%)" for i, (e, c) in enumerate(emisores, 1))
    lineas.append("")

    # 2. Distribución horaria
    lineas.append("--- 2. DISTRIBUCIÓN POR HORA DEL DÍA (00:00 A 23:00) ---")
    lineas.append("  Hora  | Mensajes | Intensidad")
    lineas.append("  ------+----------+-----------")
    max_h = max(m.conteo_horas) if m.conteo_horas else 0
    # Declarativo: generamos las 24 líneas con comprehension
    barra = lambda c: "#" * (int((c / max_h) * 35) if max_h > 0 else 0)
    lineas.extend(f"  {h:02d}:00 | {m.conteo_horas[h]:8,d} | {barra(m.conteo_horas[h])}" for h in range(24))
    lineas.append("")

    # 3. Palabras frecuentes
    lineas.append("--- 3. PALABRAS MÁS FRECUENTES ---")
    palabras = m.conteo_palabras.most_common(top_palabras_n)
    if not palabras:
        lineas.append("  (Sin palabras significativas)")
    else:
        lineas.extend(f"  {i:2d}. {p:<18} : {c:6,d} repeticiones" for i, (p, c) in enumerate(palabras, 1))
    lineas.append("")

    # 4. Por canal
    lineas.append("--- 4. MENSAJES POR CANAL / ÁREA ---")
    pct_c = lambda c: (c / m.total_mensajes * 100) if m.total_mensajes > 0 else 0
    lineas.extend(f"  * {ch:<20} : {c:6,d} msgs ({pct_c(c):5.1f}%)" for ch, c in m.conteo_canales.most_common())
    lineas.append(sep)
    return "\n".join(lineas)
