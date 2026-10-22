import socket
import struct


def recibir_exacto(sock: socket.socket, n: int) -> bytes | None:
    """Lee exactamente n bytes. Devuelve None si la conexión se cerró antes."""
    buffer = bytearray()
    while len(buffer) < n:
        # Limitar cada lectura a bloques razonables (ej. 64 KB) o a lo que falte
        por_leer = min(n - len(buffer), 65536)
        fragmento = sock.recv(por_leer)
        if not fragmento:  # equivale a fragmento == b"" (cierre del otro extremo)
            return None
        buffer.extend(fragmento)
    return bytes(buffer)


def enviar_mensaje(sock: socket.socket, texto: str) -> None:
    """Envía texto en UTF-8 precedido de su longitud en 4 bytes big-endian."""
    cuerpo = texto.encode("utf-8")
    prefijo = struct.pack("!I", len(cuerpo))
    sock.sendall(prefijo + cuerpo)


def recibir_mensaje(sock: socket.socket) -> str | None:
    """Lee un mensaje completo. Devuelve None si el otro extremo cerró."""
    prefijo = recibir_exacto(sock, 4)
    if prefijo is None:
        return None

    (longitud,) = struct.unpack("!I", prefijo)

    cuerpo = recibir_exacto(sock, longitud)
    if cuerpo is None:
        return None

    return cuerpo.decode("utf-8")