"""Script para generar reporte operativo sobre la bitácora (Hito 3)."""
import argparse, sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.config import ARCHIVO_BITACORA_POR_DEFECTO
from mensajeria.reporte import generar_reporte_desde_archivo, generar_texto_reporte


def main() -> None:
    p = argparse.ArgumentParser(description="Reporte funcional sobre bitácora.")
    p.add_argument("--bitacora", default=ARCHIVO_BITACORA_POR_DEFECTO)
    p.add_argument("--top-emisores", type=int, default=10)
    p.add_argument("--top-palabras", type=int, default=15)
    p.add_argument("--salida", default="")
    args = p.parse_args()

    ruta = Path(args.bitacora)
    if not ruta.exists():
        print(f"[ERROR] Bitácora '{ruta}' no existe. Use simular_bitacora.py para generar datos.")
        sys.exit(1)

    t0 = time.perf_counter()
    metricas = generar_reporte_desde_archivo(ruta)
    dt = time.perf_counter() - t0

    texto = generar_texto_reporte(metricas, args.top_emisores, args.top_palabras)
    print(texto)
    print(f"Procesamiento en streaming: {dt:.4f}s.")

    if args.salida:
        Path(args.salida).write_text(texto, encoding="utf-8")
        print(f"Reporte exportado a: {Path(args.salida).resolve()}")


if __name__ == "__main__":
    main()
