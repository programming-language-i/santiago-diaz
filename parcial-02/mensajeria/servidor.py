"""
PARCIAL 2 - Nivel 2 · Servidor concurrente

    python3 -m mensajeria.servidor            escucha en el puerto 8000
    python3 -m mensajeria.servidor 8050       o en el que se le diga
"""

import socket
import sys
import threading

from mensajeria.protocolo import enviar_mensaje, recibir_mensaje
from mensajeria.registro import RegistroClientes

HOST = "127.0.0.1"
PUERTO = 8000


def retransmitir(registro: RegistroClientes, emisor: str, texto: str) -> None:
    """Envía "emisor: texto" a todos los conectados menos al emisor."""
    mensaje = f"{emisor}: {texto}"
    # Requisito 4: destinatarios() devuelve una copia hecha bajo el lock,
    # por lo que el envío ocurre fuera del lock.
    for nombre_dest, sock_dest in registro.destinatarios(excepto=emisor):
        try:
            enviar_mensaje(sock_dest, mensaje)
        except OSError:
            # Requisito 5: un destinatario al que ya no se puede enviar se retira
            registro.borrar(nombre_dest)


def atender(
    conexion: socket.socket, direccion: tuple[str, int], registro: RegistroClientes
) -> None:
    """Atiende a UN cliente, en su propio hilo, hasta que se desconecta."""
    nombre_registrado: str | None = None
    # Requisito 6: usar `with` para el socket de la conexión
    with conexion:
        try:
            # Requisito 2: la primera trama del cliente es su nombre
            nombre = recibir_mensaje(conexion)
            if not nombre:
                return

            if not registro.insertar(nombre, conexion):
                enviar_mensaje(conexion, "ERROR: nombre en uso")
                return

            nombre_registrado = nombre
            enviar_mensaje(conexion, "OK")

            # Requisito 3: cada trama siguiente se retransmite a todos los demás
            while True:
                texto = recibir_mensaje(conexion)
                if texto is None:
                    break
                retransmitir(registro, nombre_registrado, texto)

        except OSError:
            # Requisito 5: una desconexión a la fuerza no tumba nada
            pass
        finally:
            # Requisito 5: si se va (con aviso o a la fuerza), se borra su entrada
            if nombre_registrado is not None:
                registro.borrar(nombre_registrado)


def main() -> None:
    # Las pruebas arrancan el servidor con un puerto libre: no cambie esta línea.
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else PUERTO
    registro = RegistroClientes()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        # Requisito 6: SO_REUSEADDR
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, puerto))
        servidor.listen()
        print(f"escuchando en {HOST}:{puerto}")
        while True:
            conexion, direccion = servidor.accept()
            # Requisito 1: un hilo por conexión; el hilo principal solo acepta
            threading.Thread(
                target=atender, args=(conexion, direccion, registro), daemon=True
            ).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nservidor detenido")