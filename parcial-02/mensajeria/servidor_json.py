"""
PARCIAL 2 · Servidor para el Nivel 3 (mensajes JSON).

    python3 -m mensajeria.servidor_json [puerto]
"""

import json
import socket
import sys
import threading
from datetime import datetime

from mensajeria.protocolo import enviar_mensaje, recibir_mensaje

HOST = "127.0.0.1"
PUERTO = 8000

# Diccionario de clientes conectados: {nombre: socket}
clientes: dict[str, socket.socket] = {}
candado = threading.Lock()


def enviar_json(sock: socket.socket, datos: dict) -> None:
    """Serializa un diccionario a JSON y lo envía por el socket."""
    try:
        enviar_mensaje(sock, json.dumps(datos, ensure_ascii=False))
    except OSError:
        pass


def enviar_error(sock: socket.socket, detalle: str) -> None:
    """Envía una trama de error al cliente que hizo un pedido inválido."""
    enviar_json(sock, {"tipo": "error", "detalle": detalle})


def atender_cliente(conexion: socket.socket) -> None:
    """Ciclo de vida de cada cliente conectado."""
    nombre = None
    try:
        # 1. Fase de saludo y registro (texto plano)
        recibido = recibir_mensaje(conexion)
        if not recibido:
            return
        candidato = recibido.strip()
        if not candidato:
            enviar_mensaje(conexion, "ERROR: Nombre vacío")
            return

        with candado:
            if candidato in clientes:
                enviar_mensaje(conexion, "ERROR: Nombre en uso")
                return
            nombre = candidato
            clientes[nombre] = conexion

        enviar_mensaje(conexion, "OK")

        # 2. Fase de mensajería JSON
        while True:
            trama = recibir_mensaje(conexion)
            if trama is None:
                break

            # Paso 5: Validar que la trama sea un objeto JSON válido
            try:
                pedido = json.loads(trama)
            except json.JSONDecodeError:
                # Se descarta el JSON dañado (o se envía error) y la conexión sigue
                continue

            if not isinstance(pedido, dict):
                enviar_error(conexion, "El pedido debe ser un objeto JSON.")
                continue

            tipo = pedido.get("tipo")
            contenido = pedido.get("contenido")

            # Paso 4: Validar que el tipo sea conocido
            if tipo not in ("mensaje", "privado"):
                enviar_error(conexion, f"Tipo de pedido desconocido: {tipo!r}")
                continue

            # Paso 4: Validar que exista contenido válido
            if not isinstance(contenido, str) or not contenido:
                enviar_error(conexion, "El mensaje debe tener contenido.")
                continue

            # Paso 1 y 3: El servidor genera el timestamp y fuerza el emisor real
            ahora = datetime.now().isoformat(timespec="seconds")

            if tipo == "mensaje":
                respuesta = {
                    "tipo": "mensaje",
                    "emisor": nombre,
                    "canal": "general",
                    "contenido": contenido,
                    "timestamp": ahora,
                }
                with candado:
                    destinos = [
                        sock for usr, sock in clientes.items() if usr != nombre
                    ]
                for sock in destinos:
                    enviar_json(sock, respuesta)

            elif tipo == "privado":
                destino = pedido.get("destino")
                if not isinstance(destino, str) or not destino:
                    enviar_error(conexion, "Falta especificar el destinatario.")
                    continue

                # Paso 4: No se permite enviarse privados a uno mismo
                if destino == nombre:
                    enviar_error(conexion, "No puedes enviarte un privado a ti mismo.")
                    continue

                with candado:
                    sock_destino = clientes.get(destino)

                # Paso 4: Validar que el destinatario esté conectado
                if sock_destino is None:
                    enviar_error(conexion, f"El usuario '{destino}' no está conectado.")
                    continue

                # Paso 2 y 3: Enviar privado solo al destino con el emisor real
                respuesta = {
                    "tipo": "privado",
                    "emisor": nombre,
                    "destino": destino,
                    "contenido": contenido,
                    "timestamp": ahora,
                }
                enviar_json(sock_destino, respuesta)

    except OSError:
        pass
    finally:
        if nombre is not None:
            with candado:
                if clientes.get(nombre) is conexion:
                    del clientes[nombre]
        try:
            conexion.close()
        except OSError:
            pass


def main() -> None:
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else PUERTO
    sys.stdout.reconfigure(errors="replace")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, puerto))
        servidor.listen()
        print(f"Servidor JSON escuchando en {HOST}:{puerto}...")

        try:
            while True:
                conexion, _ = servidor.accept()
                threading.Thread(
                    target=atender_cliente, args=(conexion,), daemon=True
                ).start()
        except KeyboardInterrupt:
            print("\nDeteniendo el servidor.")


if __name__ == "__main__":
    main()