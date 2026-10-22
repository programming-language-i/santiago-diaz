import logging, socket, sys, threading, time, uuid
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.bitacora import BitacoraAuditable
from mensajeria.config import (
    ARCHIVO_BITACORA_POR_DEFECTO, CANAL_GENERAL, CANALES_FIJOS,
    HOST_POR_DEFECTO, INTERVALO_VERIFICACION_DISPONIBILIDAD,
    PUERTO_TCP_POR_DEFECTO, PUERTO_UDP_POR_DEFECTO, TIEMPO_INACTIVIDAD_SEGUNDOS,
)
from mensajeria.estado import EstadoDisponibilidad, RegistroConectados, Usuario
from mensajeria.protocolo import (
    ConexionCerradaError, TramaInvalidaError, enviar_mensaje_tcp,
    recibir_mensaje_tcp, recibir_mensaje_udp,
    TIPO_DIFUSION_CANAL, TIPO_DIFUSION_PRIVADA, TIPO_ERROR, TIPO_HEARTBEAT,
    TIPO_LISTAR_CANALES, TIPO_LISTAR_USUARIOS, TIPO_LOGIN, TIPO_LOGIN_EXITO,
    TIPO_MENSAJE_CANAL, TIPO_MENSAJE_PRIVADO, TIPO_NOTIFICACION_SISTEMA,
    TIPO_RESPUESTA_CANALES, TIPO_RESPUESTA_USUARIOS, TIPO_SALIR_CANAL, TIPO_UNIR_CANAL,
)
from mensajeria.utilidades import obtener_timestamp_iso

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s")
logger = logging.getLogger("ServidorMensajeria")


class ServidorMensajeria:
    """Servidor concurrente multihilo TCP+UDP."""

    def __init__(self, host: str = HOST_POR_DEFECTO, puerto_tcp: int = PUERTO_TCP_POR_DEFECTO,
                 puerto_udp: int = PUERTO_UDP_POR_DEFECTO, ruta_bitacora: str | Path = ARCHIVO_BITACORA_POR_DEFECTO) -> None:
        self.host, self.puerto_tcp, self.puerto_udp = host, puerto_tcp, puerto_udp
        self.registro = RegistroConectados()
        self.bitacora = BitacoraAuditable(ruta_bitacora)
        self._activo = False
        self._socket_tcp: socket.socket | None = None
        self._socket_udp: socket.socket | None = None

    def _crear_hilo(self, target: Any, name: str) -> threading.Thread:
        """Helper imperativo para crear hilos daemon."""
        h = threading.Thread(target=target, name=name, daemon=True)
        h.start()
        return h

    def iniciar(self) -> None:
        """Inicia sockets y lanza hilos de escucha."""
        self._activo = True
        # TCP
        s_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_tcp.bind((self.host, self.puerto_tcp))
        s_tcp.listen()
        self._socket_tcp = s_tcp
        logger.info("TCP en %s:%d", self.host, self.puerto_tcp)
        # UDP
        s_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_udp.bind((self.host, self.puerto_udp))
        self._socket_udp = s_udp
        logger.info("UDP en %s:%d", self.host, self.puerto_udp)
        # Hilos
        self._crear_hilo(self._bucle_aceptar_tcp, "TCP-Acceptor")
        self._crear_hilo(self._bucle_escuchar_udp, "UDP-Heartbeat")
        self._crear_hilo(self._bucle_verificar_disponibilidad, "Monitor-Disponibilidad")

    def detener(self) -> None:
        """Detiene servidor y cierra sockets."""
        logger.info("Deteniendo servidor...")
        self._activo = False
        # Cerrar sockets del servidor
        for s in (self._socket_tcp, self._socket_udp):
            if s:
                try: s.close()
                except OSError: pass
        # Cerrar sockets de clientes
        for u in self.registro.obtener_todos():
            try: u.socket_tcp.close()
            except OSError: pass
        logger.info("Servidor detenido.")

    # --- TCP ---
    def _bucle_aceptar_tcp(self) -> None:
        while self._activo and self._socket_tcp:
            try:
                sock, addr = self._socket_tcp.accept()
                logger.info("Conexión desde %s:%d", *addr)
                self._crear_hilo(lambda s=sock, a=addr: self._atender_cliente_tcp(s, a),
                                 f"Cliente-{addr[0]}:{addr[1]}")
            except OSError:
                break

    def _atender_cliente_tcp(self, sock: socket.socket, addr: tuple[str, int]) -> None:
        """Ciclo de vida completo de un cliente TCP."""
        usuario: Usuario | None = None
        try:
            # Login (Req 01)
            datos = recibir_mensaje_tcp(sock)
            if datos.get("tipo") != TIPO_LOGIN:
                enviar_mensaje_tcp(sock, {"tipo": TIPO_ERROR, "mensaje": "Se esperaba 'login'."})
                return

            nombre = str(datos.get("usuario", "")).strip()
            ok, motivo, usuario = self.registro.registrar_usuario(nombre, sock, addr)
            if not ok or not usuario:
                logger.warning("Rechazado '%s': %s", nombre, motivo)
                enviar_mensaje_tcp(sock, {"tipo": TIPO_ERROR, "mensaje": motivo})
                return

            logger.info("'%s' autenticado desde %s", usuario.nombre, addr)
            enviar_mensaje_tcp(sock, {
                "tipo": TIPO_LOGIN_EXITO, "usuario": usuario.nombre,
                "canales": sorted(usuario.canales), "todos_los_canales": list(CANALES_FIJOS),
                "mensaje": f"Bienvenido, {usuario.nombre}.",
            })
            self._difundir_sistema(CANAL_GENERAL, f"'{usuario.nombre}' se ha conectado.")

            # Bucle de mensajes
            while self._activo:
                try:
                    msg = recibir_mensaje_tcp(sock)
                except TramaInvalidaError as e:
                    logger.warning("Trama inválida de '%s': %s", usuario.nombre, e)
                    try: enviar_mensaje_tcp(sock, {"tipo": TIPO_ERROR, "mensaje": f"Trama descartada: {e}"})
                    except Exception: break
                    continue
                usuario.actualizar_actividad()
                self._procesar_mensaje(usuario, msg)

        except ConexionCerradaError:
            logger.info("Desconexión de %s", usuario.nombre if usuario else addr)
        except Exception as e:
            logger.error("Error en %s: %s", usuario.nombre if usuario else addr, e)
        finally:
            self._limpiar_desconexion(sock, usuario)

    def _procesar_mensaje(self, u: Usuario, msg: dict[str, Any]) -> None:
        """Despacha mensajes por tipo usando dict declarativo."""
        tipo = str(msg.get("tipo", ""))
        handlers = {
            TIPO_MENSAJE_CANAL: lambda: self._msg_canal(u, msg),
            TIPO_MENSAJE_PRIVADO: lambda: self._msg_privado(u, msg),
            TIPO_UNIR_CANAL: lambda: self._unir_canal(u, msg),
            TIPO_SALIR_CANAL: lambda: self._salir_canal(u, msg),
            TIPO_LISTAR_CANALES: lambda: self._listar_canales(u),
            TIPO_LISTAR_USUARIOS: lambda: self._listar_usuarios(u),
        }
        handler = handlers.get(tipo)
        if handler:
            handler()
        else:
            enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_ERROR, "mensaje": f"Tipo '{tipo}' no reconocido."})

    # --- Handlers ---
    def _msg_canal(self, u: Usuario, msg: dict[str, Any]) -> None:
        canal, texto = str(msg.get("canal", "")).strip().lower(), str(msg.get("texto", "")).strip()
        if not texto:
            enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_ERROR, "mensaje": "Mensaje vacío."})
            return
        if canal not in u.canales:
            enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_ERROR, "mensaje": f"No eres miembro de '{canal}'."})
            return
        trama = {"tipo": TIPO_DIFUSION_CANAL, "id": str(uuid.uuid4()), "emisor": u.nombre,
                 "canal": canal, "texto": texto, "timestamp": obtener_timestamp_iso()}
        self.bitacora.registrar_mensaje(trama)
        for m in self.registro.obtener_destinatarios_canal(canal):
            try: enviar_mensaje_tcp(m.socket_tcp, trama)
            except ConexionCerradaError: pass

    def _msg_privado(self, u: Usuario, msg: dict[str, Any]) -> None:
        dest_nombre, texto = str(msg.get("destinatario", "")).strip(), str(msg.get("texto", "")).strip()
        if not texto:
            enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_ERROR, "mensaje": "Mensaje privado vacío."})
            return
        dest = self.registro.obtener_usuario(dest_nombre)
        if not dest:
            enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_ERROR, "mensaje": f"'{dest_nombre}' no está conectado."})
            return
        if dest.nombre.lower() == u.nombre.lower():
            enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_ERROR, "mensaje": "No puedes enviarte un mensaje a ti mismo."})
            return
        trama = {"tipo": TIPO_DIFUSION_PRIVADA, "id": str(uuid.uuid4()), "emisor": u.nombre,
                 "destinatario": dest.nombre, "texto": texto, "timestamp": obtener_timestamp_iso()}
        self.bitacora.registrar_mensaje(trama)
        try: enviar_mensaje_tcp(dest.socket_tcp, trama)
        except ConexionCerradaError:
            enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_ERROR, "mensaje": f"Fallo al entregar a '{dest.nombre}'."})
            return
        try: enviar_mensaje_tcp(u.socket_tcp, trama)
        except ConexionCerradaError: pass

    def _unir_canal(self, u: Usuario, msg: dict[str, Any]) -> None:
        canal = str(msg.get("canal", ""))
        ok, razon = self.registro.unir_a_canal(u.nombre, canal)
        enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_NOTIFICACION_SISTEMA, "mensaje": razon,
                                          "exito": ok, "canales": sorted(u.canales)})
        if ok:
            c = canal.strip().lower()
            c = c if c.startswith("#") else f"#{c}"
            self._difundir_sistema(c, f"'{u.nombre}' se unió a {c}.", excluir=u.nombre)

    def _salir_canal(self, u: Usuario, msg: dict[str, Any]) -> None:
        canal = str(msg.get("canal", ""))
        ok, razon = self.registro.salir_de_canal(u.nombre, canal)
        enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_NOTIFICACION_SISTEMA, "mensaje": razon,
                                          "exito": ok, "canales": sorted(u.canales)})
        if ok:
            c = canal.strip().lower()
            c = c if c.startswith("#") else f"#{c}"
            self._difundir_sistema(c, f"'{u.nombre}' salió de {c}.")

    def _listar_canales(self, u: Usuario) -> None:
        enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_RESPUESTA_CANALES,
                                          "canales_disponibles": list(CANALES_FIJOS), "mis_canales": sorted(u.canales)})

    def _listar_usuarios(self, u: Usuario) -> None:
        enviar_mensaje_tcp(u.socket_tcp, {"tipo": TIPO_RESPUESTA_USUARIOS,
                                          "usuarios": [x.to_dict() for x in self.registro.obtener_todos()]})

    def _difundir_sistema(self, canal: str, mensaje: str, excluir: str | None = None) -> None:
        trama = {"tipo": TIPO_NOTIFICACION_SISTEMA, "canal": canal, "mensaje": mensaje,
                 "timestamp": obtener_timestamp_iso()}
        for u in self.registro.obtener_destinatarios_canal(canal):
            if excluir and u.nombre == excluir:
                continue
            try: enviar_mensaje_tcp(u.socket_tcp, trama)
            except ConexionCerradaError: pass

    def _limpiar_desconexion(self, sock: socket.socket, usuario: Usuario | None) -> None:
        try: sock.close()
        except OSError: pass
        eliminado = self.registro.desregistrar_por_socket(sock)
        nombre = (usuario.nombre if usuario else eliminado.nombre if eliminado else None)
        if nombre:
            logger.info("'%s' desregistrado.", nombre)
            self._difundir_sistema(CANAL_GENERAL, f"'{nombre}' se ha desconectado.")

    # --- UDP ---
    def _bucle_escuchar_udp(self) -> None:
        while self._activo and self._socket_udp:
            try:
                datos, addr = recibir_mensaje_udp(self._socket_udp)
                if datos.get("tipo") == TIPO_HEARTBEAT:
                    nombre = str(datos.get("usuario", "")).strip()
                    if nombre and self.registro.actualizar_actividad(nombre):
                        logger.debug("Heartbeat de '%s' (%s)", nombre, addr)
            except TramaInvalidaError:
                continue
            except OSError:
                break

    def _bucle_verificar_disponibilidad(self) -> None:
        while self._activo:
            time.sleep(INTERVALO_VERIFICACION_DISPONIBILIDAD)
            if not self._activo:
                break
            for u, estado in self.registro.verificar_disponibilidad(TIEMPO_INACTIVIDAD_SEGUNDOS):
                if estado == EstadoDisponibilidad.INACTIVO:
                    logger.info("'%s' marcado INACTIVO.", u.nombre)


if __name__ == "__main__":
    servidor = ServidorMensajeria()
    servidor.iniciar()
    print(f"\n[SERVIDOR] Activo en {servidor.host}:{servidor.puerto_tcp} (TCP) y :{servidor.puerto_udp} (UDP).")
    print("[SERVIDOR] Presiona Ctrl+C para detener.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        servidor.detener()

