"""Script para iniciar una estación de cliente."""
import argparse, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.cliente import ClienteMensajeria
from mensajeria.config import HOST_POR_DEFECTO, PUERTO_TCP_POR_DEFECTO, PUERTO_UDP_POR_DEFECTO


def main() -> None:
    p = argparse.ArgumentParser(description="Estación de cliente de mensajería.")
    p.add_argument("-u", "--usuario", default="")
    p.add_argument("--host", default=HOST_POR_DEFECTO)
    p.add_argument("--tcp", type=int, default=PUERTO_TCP_POR_DEFECTO)
    p.add_argument("--udp", type=int, default=PUERTO_UDP_POR_DEFECTO)
    args = p.parse_args()

    usuario = args.usuario.strip()
    if not usuario:
        try:
            print("=" * 55 + "\n ESTACIÓN DE TRABAJO - MENSAJERÍA INTERNA\n" + "=" * 55)
            usuario = input("Nombre de usuario: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelado.")
            return

    if not usuario:
        print("[ERROR] Nombre vacío.")
        sys.exit(1)

    cliente = ClienteMensajeria(usuario, args.host, args.tcp, args.udp)
    if cliente.conectar():
        cliente.ejecutar_consola()
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
