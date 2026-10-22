"""
PARCIAL 2 - Nivel 2 (20 pts) · Registro de clientes

Quién está conectado: un dict con el nombre como clave, protegido con UN
threading.Lock. Lo usan a la vez todos los hilos del servidor.
"""

import socket
import threading


class RegistroClientes:
    def __init__(self) -> None:
        self.clientes: dict[str, socket.socket] = {}
        self.lock = threading.Lock()

    def insertar(self, nombre: str, conexion: socket.socket) -> bool:
        with self.lock:
            if nombre in self.clientes:
                return False
            self.clientes[nombre] = conexion
            return True

    def buscar(self, nombre: str) -> socket.socket | None:
        with self.lock:
            return self.clientes.get(nombre)

    def borrar(self, nombre: str) -> None:
        with self.lock:
            self.clientes.pop(nombre, None)

    def destinatarios(self, excepto: str) -> list[tuple[str, socket.socket]]:
        with self.lock:
            return [
                (nombre, conn)
                for nombre, conn in self.clientes.items()
                if nombre != excepto
            ]