"""
PARCIAL 2 · Cliente de consola para el Nivel 2 (completo: no se modifica)

    python3 -m mensajeria.cliente camilo             se conecta al puerto 8000
    python3 -m mensajeria.cliente camilo 8050        o al que se le diga

Dos hilos: el principal lee del teclado y envía; el otro recibe y muestra.
Se sale escribiendo 0. Usa su protocolo.py: sin el Nivel 1 no funciona.
"""

import socket
import sys
import threading

from mensajeria.protocolo import enviar_mensaje, recibir_mensaje

HOST = "127.0.0.1"
PUERTO = 8000


def recibir_mensajes(conexion: socket.socket) -> None:
    while True:
        try:
            texto = recibir_mensaje(conexion)
        except OSError:
            texto = None
        if texto is None:
            print("\nServidor desconectado. Escriba 0 para salir.")
            break
        print(f"\n{texto}")
        print("> ", end="", flush=True)


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python3 -m mensajeria.cliente <nombre> [puerto]")
        return
    nombre = sys.argv[1]
    puerto = int(sys.argv[2]) if len(sys.argv) > 2 else PUERTO
    sys.stdout.reconfigure(
        errors="replace"
    )  # una consola sin emojis no tumba al cliente

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
        cliente.connect((HOST, puerto))
        enviar_mensaje(cliente, nombre)  # la primera trama es el nombre
        respuesta = recibir_mensaje(cliente)
        if respuesta != "OK":
            print(f"El servidor respondió: {respuesta}")
            return

        print(f"Conectado como {nombre}. Escriba mensajes; 0 para terminar.")
        threading.Thread(target=recibir_mensajes, args=(cliente,), daemon=True).start()

        while True:
            try:
                texto = input("> ")
            except (EOFError, KeyboardInterrupt):
                break
            if texto == "0":
                break
            if not texto:
                continue
            try:
                enviar_mensaje(cliente, texto)
            except OSError:
                print("No se pudo enviar: la conexión se cerró.")
                break


if __name__ == "__main__":
    main()