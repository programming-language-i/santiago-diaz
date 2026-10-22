import json, os, sys, threading
from pathlib import Path
from typing import Any, Iterator

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.config import ARCHIVO_BITACORA_POR_DEFECTO


class BitacoraAuditable:
    """Registro auditable y persistente de mensajes en disco."""

    def __init__(self, ruta: str | Path = ARCHIVO_BITACORA_POR_DEFECTO) -> None:
        self.ruta = Path(ruta)
        self._lock = threading.Lock()
        if self.ruta.parent and not self.ruta.parent.exists():
            self.ruta.parent.mkdir(parents=True, exist_ok=True)

    def registrar_mensaje(self, datos: dict[str, Any]) -> None:
        """Registra un mensaje en disco de forma atómica y thread-safe con fsync."""
        linea = json.dumps(datos, ensure_ascii=False).encode("utf-8") + b"\n"
        with self._lock:
            with open(self.ruta, "ab") as f:
                f.write(linea)
                f.flush()
                os.fsync(f.fileno())

    def iterar_mensajes(self) -> Iterator[dict[str, Any]]:
        """Generador perezoso que lee mensajes línea por línea (memoria O(1))."""
        if not self.ruta.exists():
            return
        with open(self.ruta, "r", encoding="utf-8", errors="replace") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    reg = json.loads(linea)
                    if isinstance(reg, dict):
                        yield reg
                except json.JSONDecodeError:
                    continue  # Líneas corruptas se descartan

    def contar_mensajes(self) -> int:
        """Declarativo: cuenta mensajes usando el generador perezoso."""
        return sum(1 for _ in self.iterar_mensajes())
