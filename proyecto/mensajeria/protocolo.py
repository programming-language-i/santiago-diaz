import json, socket, struct, sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.config import (
    BUFFER_RECEPCION_SOCKET_BYTES,
    MAXIMO_TAMANO_PAYLOAD_BYTES,
    TAMANO_PREFIJO_LONGITUD_BYTES,
)

# Constantes de tipos de mensajes
TIPO_LOGIN = "login"
TIPO_LOGIN_EXITO = "login_exito"
TIPO_ERROR = "error"
TIPO_MENSAJE_CANAL = "mensaje_canal"
TIPO_DIFUSION_CANAL = "difusion_canal"
TIPO_MENSAJE_PRIVADO = "mensaje_privado"
TIPO_DIFUSION_PRIVADA = "difusion_privada"
TIPO_UNIR_CANAL = "unir_canal"
TIPO_SALIR_CANAL = "salir_canal"
TIPO_LISTAR_CANALES = "listar_canales"
TIPO_RESPUESTA_CANALES = "respuesta_canales"
TIPO_LISTAR_USUARIOS = "listar_usuarios"
TIPO_RESPUESTA_USUARIOS = "respuesta_usuarios"
TIPO_HEARTBEAT = "heartbeat"
TIPO_NOTIFICACION_SISTEMA = "notificacion_sistema"


# Excepciones
class ErrorProtocolo(Exception): pass
class ConexionCerradaError(ErrorProtocolo): pass
class TramaInvalidaError(ErrorProtocolo): pass


def codificar_trama_tcp(datos: dict[str, Any]) -> bytes:
    """Codifica dict a bytes con prefijo de longitud de 4 bytes big-endian."""
    try:
        payload = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise TramaInvalidaError(f"No se pudo serializar a JSON: {e}") from e
    if len(payload) > MAXIMO_TAMANO_PAYLOAD_BYTES:
        raise TramaInvalidaError(f"Payload ({len(payload)}B) excede máximo ({MAXIMO_TAMANO_PAYLOAD_BYTES}B)")
    return struct.pack("!I", len(payload)) + payload


def _recibir_exactamente(sock: socket.socket, n: int) -> bytes:
    """Lee exactamente n bytes del socket TCP."""
    buf = bytearray()
    while len(buf) < n:
        try:
            chunk = sock.recv(min(n - len(buf), BUFFER_RECEPCION_SOCKET_BYTES))
        except (ConnectionResetError, BrokenPipeError, TimeoutError, OSError) as e:
            raise ConexionCerradaError(f"Error de red: {e}") from e
        if not chunk:
            if not buf:
                raise ConexionCerradaError("Conexión cerrada por el remoto.")
            raise TramaInvalidaError(f"Conexión cerrada a mitad de trama ({len(buf)}/{n} bytes)")
        buf.extend(chunk)
    return bytes(buf)


def recibir_mensaje_tcp(sock: socket.socket) -> dict[str, Any]:
    """Recibe y decodifica un mensaje TCP completo con framing por longitud."""
    prefijo = _recibir_exactamente(sock, TAMANO_PREFIJO_LONGITUD_BYTES)
    longitud = struct.unpack("!I", prefijo)[0]
    if longitud <= 0 or longitud > MAXIMO_TAMANO_PAYLOAD_BYTES:
        raise TramaInvalidaError(f"Longitud de trama inválida: {longitud}")
    payload = _recibir_exactamente(sock, longitud)
    try:
        datos = json.loads(payload.decode("utf-8"))
        if not isinstance(datos, dict):
            raise TramaInvalidaError("Payload no es un objeto JSON.")
        return datos
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise TramaInvalidaError(f"Trama con contenido inválido: {e}") from e


def enviar_mensaje_tcp(sock: socket.socket, datos: dict[str, Any]) -> None:
    """Envía un dict por TCP con framing por longitud."""
    try:
        sock.sendall(codificar_trama_tcp(datos))
    except (ConnectionResetError, BrokenPipeError, TimeoutError, OSError) as e:
        raise ConexionCerradaError(f"Error al enviar: {e}") from e


def enviar_mensaje_udp(sock: socket.socket, datos: dict[str, Any], direccion: tuple[str, int]) -> None:
    """Envía un datagrama UDP con payload JSON."""
    try:
        sock.sendto(json.dumps(datos, ensure_ascii=False).encode("utf-8"), direccion)
    except Exception as e:
        raise ErrorProtocolo(f"Error UDP a {direccion}: {e}") from e


def recibir_mensaje_udp(sock: socket.socket, buf_size: int = BUFFER_RECEPCION_SOCKET_BYTES) -> tuple[dict[str, Any], tuple[str, int]]:
    """Recibe datagrama UDP y deserializa JSON. Retorna (datos, direccion)."""
    raw, addr = sock.recvfrom(buf_size)
    try:
        datos = json.loads(raw.decode("utf-8"))
        if not isinstance(datos, dict):
            raise TramaInvalidaError("Datagrama UDP no es un objeto JSON.")
        return datos, addr
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise TramaInvalidaError(f"Datagrama UDP inválido: {e}") from e
