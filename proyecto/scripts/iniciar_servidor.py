"""Script para iniciar el servidor de mensajería."""
import argparse, sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.config import (ARCHIVO_BITACORA_POR_DEFECTO, HOST_POR_DEFECTO,
                                PUERTO_TCP_POR_DEFECTO, PUERTO_UDP_POR_DEFECTO)
from mensajeria.servidor import ServidorMensajeria


def main() -> None:
    p = argparse.ArgumentParser(description="Servidor de mensajería interna.")
    p.add_argument("--host", default=HOST_POR_DEFECTO)
    p.add_argument("--tcp", type=int, default=PUERTO_TCP_POR_DEFECTO)
    p.add_argument("--udp", type=int, default=PUERTO_UDP_POR_DEFECTO)
    p.add_argument("--bitacora", default=ARCHIVO_BITACORA_POR_DEFECTO)
    args = p.parse_args()

    print(f"{'='*60}\n SERVIDOR DE MENSAJERÍA - CENTRO DE DISTRIBUCIÓN\n{'='*60}")
    print(f" Host: {args.host}  TCP: {args.tcp}  UDP: {args.udp}  Bitácora: {args.bitacora}")
    print(" Ctrl+C para detener.\n" + "="*60)

    srv = ServidorMensajeria(args.host, args.tcp, args.udp, args.bitacora)
    try:
        srv.iniciar()
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[AVISO] Interrupción recibida.")
    finally:
        srv.detener()


if __name__ == "__main__":
    main()
