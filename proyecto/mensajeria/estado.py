from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import socket, sys, threading, time
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.config import CANAL_GENERAL, CANALES_FIJOS, TIEMPO_INACTIVIDAD_SEGUNDOS


class EstadoDisponibilidad(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"


@dataclass
class Usuario:
    """Operario conectado al sistema."""
    nombre: str
    socket_tcp: socket.socket
    direccion_ip: str
    puerto_tcp: int
    canales: set[str] = field(default_factory=lambda: {CANAL_GENERAL})
    estado: EstadoDisponibilidad = EstadoDisponibilidad.ACTIVO
    ultima_actividad: float = field(default_factory=time.time)
    conectado_en: float = field(default_factory=time.time)

    def actualizar_actividad(self) -> None:
        self.ultima_actividad = time.time()
        self.estado = EstadoDisponibilidad.ACTIVO

    def to_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "estado": self.estado.value,
            "canales": sorted(self.canales),
            "direccion_ip": self.direccion_ip,
            "segundos_desde_actividad": round(max(0.0, time.time() - self.ultima_actividad), 1),
            "conectado_en": self.conectado_en,
        }


class RegistroConectados:
    """Registro concurrente (thread-safe) de usuarios y canales."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._usuarios: dict[str, Usuario] = {}
        self._sockets: dict[socket.socket, str] = {}

    def registrar_usuario(self, nombre: str, sock: socket.socket, direccion: tuple[str, int]) -> tuple[bool, str, Usuario | None]:
        """Registra usuario con identidad única (Req 01)."""
        nombre = nombre.strip()
        if not nombre:
            return False, "El nombre no puede estar vacío.", None
        if len(nombre) > 30:
            return False, "El nombre no debe superar 30 caracteres.", None

        with self._lock:
            # Imperativo: recorremos y validamos colisión case-insensitive
            if any(u.nombre.lower() == nombre.lower() for u in self._usuarios.values()):
                return False, f"Ya existe una sesión activa con el nombre '{nombre}'.", None

            ip, puerto = direccion
            usuario = Usuario(nombre=nombre, socket_tcp=sock, direccion_ip=ip, puerto_tcp=puerto,
                              canales={CANAL_GENERAL}, estado=EstadoDisponibilidad.ACTIVO,
                              ultima_actividad=time.time(), conectado_en=time.time())
            self._usuarios[nombre] = usuario
            self._sockets[sock] = nombre
            return True, "Conexión autorizada.", usuario

    def desregistrar_por_socket(self, sock: socket.socket) -> Usuario | None:
        with self._lock:
            nombre = self._sockets.pop(sock, None)
            return self._usuarios.pop(nombre, None) if nombre else None

    def desregistrar_por_nombre(self, nombre: str) -> Usuario | None:
        with self._lock:
            usuario = self._usuarios.pop(nombre, None)
            if usuario:
                self._sockets.pop(usuario.socket_tcp, None)
            return usuario

    def obtener_usuario(self, nombre: str) -> Usuario | None:
        with self._lock:
            if nombre in self._usuarios:
                return self._usuarios[nombre]
            # Búsqueda case-insensitive con next + generador
            nl = nombre.lower()
            return next((u for u in self._usuarios.values() if u.nombre.lower() == nl), None)

    def obtener_usuario_por_socket(self, sock: socket.socket) -> Usuario | None:
        with self._lock:
            nombre = self._sockets.get(sock)
            return self._usuarios.get(nombre) if nombre else None

    def actualizar_actividad(self, nombre: str) -> bool:
        with self._lock:
            usuario = self.obtener_usuario(nombre)
            if usuario:
                usuario.actualizar_actividad()
                return True
            return False

    def _normalizar_canal(self, canal: str) -> str:
        """Lambda-like helper para normalizar nombre de canal."""
        c = canal.strip().lower()
        return c if c.startswith("#") else f"#{c}"

    def unir_a_canal(self, nombre: str, canal: str) -> tuple[bool, str]:
        canal_fmt = self._normalizar_canal(canal)
        if canal_fmt not in CANALES_FIJOS:
            return False, f"Canal desconocido '{canal}'. Válidos: {', '.join(CANALES_FIJOS)}"
        with self._lock:
            usuario = self.obtener_usuario(nombre)
            if not usuario:
                return False, f"Usuario '{nombre}' no encontrado."
            if canal_fmt in usuario.canales:
                return False, f"Ya perteneces al canal {canal_fmt}."
            usuario.canales.add(canal_fmt)
            usuario.actualizar_actividad()
            return True, f"Te has unido al canal {canal_fmt}."

    def salir_de_canal(self, nombre: str, canal: str) -> tuple[bool, str]:
        canal_fmt = self._normalizar_canal(canal)
        if canal_fmt == CANAL_GENERAL:
            return False, f"No puedes abandonar {CANAL_GENERAL}."
        with self._lock:
            usuario = self.obtener_usuario(nombre)
            if not usuario:
                return False, f"Usuario '{nombre}' no encontrado."
            if canal_fmt not in usuario.canales:
                return False, f"No formas parte de {canal_fmt}."
            usuario.canales.remove(canal_fmt)
            usuario.actualizar_actividad()
            return True, f"Has salido del canal {canal_fmt}."

    # Declarativo: list comprehension para filtrar miembros
    def obtener_destinatarios_canal(self, canal: str) -> list[Usuario]:
        with self._lock:
            return [u for u in self._usuarios.values() if canal in u.canales]

    def obtener_todos(self) -> list[Usuario]:
        with self._lock:
            return list(self._usuarios.values())

    def verificar_disponibilidad(self, umbral_segundos: float = TIEMPO_INACTIVIDAD_SEGUNDOS) -> list[tuple[Usuario, EstadoDisponibilidad]]:
        """Marca como INACTIVO a quienes superen el umbral (Req 08)."""
        ahora = time.time()
        cambios: list[tuple[Usuario, EstadoDisponibilidad]] = []
        with self._lock:
            for u in self._usuarios.values():
                if ahora - u.ultima_actividad > umbral_segundos and u.estado == EstadoDisponibilidad.ACTIVO:
                    u.estado = EstadoDisponibilidad.INACTIVO
                    cambios.append((u, EstadoDisponibilidad.INACTIVO))
        return cambios
