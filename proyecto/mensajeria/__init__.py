import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.bitacora import BitacoraAuditable
from mensajeria.cliente import ClienteMensajeria
from mensajeria.config import (
    ARCHIVO_BITACORA_POR_DEFECTO, CANALES_FIJOS, HOST_POR_DEFECTO,
    PUERTO_TCP_POR_DEFECTO, PUERTO_UDP_POR_DEFECTO,
)
from mensajeria.estado import EstadoDisponibilidad, RegistroConectados, Usuario
from mensajeria.protocolo import (
    ConexionCerradaError, ErrorProtocolo, TramaInvalidaError,
    enviar_mensaje_tcp, enviar_mensaje_udp, recibir_mensaje_tcp, recibir_mensaje_udp,
)
from mensajeria.reporte import generar_reporte_desde_archivo, generar_texto_reporte
from mensajeria.servidor import ServidorMensajeria

__all__ = [
    "ServidorMensajeria", "ClienteMensajeria", "BitacoraAuditable",
    "RegistroConectados", "Usuario", "EstadoDisponibilidad",
    "generar_reporte_desde_archivo", "generar_texto_reporte",
    "ErrorProtocolo", "ConexionCerradaError", "TramaInvalidaError",
    "enviar_mensaje_tcp", "recibir_mensaje_tcp", "enviar_mensaje_udp", "recibir_mensaje_udp",
    "HOST_POR_DEFECTO", "PUERTO_TCP_POR_DEFECTO", "PUERTO_UDP_POR_DEFECTO",
    "CANALES_FIJOS", "ARCHIVO_BITACORA_POR_DEFECTO",
]
