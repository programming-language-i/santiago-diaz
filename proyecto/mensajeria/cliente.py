import socket, sys, threading, time
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.config import (
    CANAL_GENERAL, HOST_POR_DEFECTO, INTERVALO_HEARTBEAT_SEGUNDOS,
    PUERTO_TCP_POR_DEFECTO, PUERTO_UDP_POR_DEFECTO,
)
from mensajeria.protocolo import (
    ConexionCerradaError, TramaInvalidaError, enviar_mensaje_tcp,
    enviar_mensaje_udp, recibir_mensaje_tcp,
    TIPO_DIFUSION_CANAL, TIPO_DIFUSION_PRIVADA, TIPO_ERROR, TIPO_HEARTBEAT,
    TIPO_LISTAR_CANALES, TIPO_LISTAR_USUARIOS, TIPO_LOGIN, TIPO_LOGIN_EXITO,
    TIPO_MENSAJE_CANAL, TIPO_MENSAJE_PRIVADO, TIPO_NOTIFICACION_SISTEMA,
    TIPO_RESPUESTA_CANALES, TIPO_RESPUESTA_USUARIOS, TIPO_SALIR_CANAL, TIPO_UNIR_CANAL,
)
from mensajeria.utilidades import formatear_hora_corta


class ClienteMensajeria:
    """Cliente de mensajería para estaciones de trabajo."""

    def __init__(self, usuario: str, host: str = HOST_POR_DEFECTO, puerto_tcp: int = PUERTO_TCP_POR_DEFECTO,
                 puerto_udp: int = PUERTO_UDP_POR_DEFECTO) -> None:
        self.usuario = usuario.strip()
        self.host, self.puerto_tcp, self.puerto_udp = host, puerto_tcp, puerto_udp
        self.canal_actual = CANAL_GENERAL
        self.mis_canales: set[str] = {CANAL_GENERAL}
        self._sock_tcp: socket.socket | None = None
        self._sock_udp: socket.socket | None = None
        self._conectado = False

    def conectar(self) -> bool:
        """Conecta al servidor TCP y realiza login."""
        try:
            s_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s_tcp.connect((self.host, self.puerto_tcp))
            enviar_mensaje_tcp(s_tcp, {"tipo": TIPO_LOGIN, "usuario": self.usuario})

            resp = recibir_mensaje_tcp(s_tcp)
            if resp.get("tipo") != TIPO_LOGIN_EXITO:
                print(f"\n[ERROR] {resp.get('mensaje', 'Fallo de autenticación.')}")
                s_tcp.close()
                return False

            self._sock_tcp = s_tcp
            self._conectado = True
            self.mis_canales = set(resp.get("canales", [CANAL_GENERAL]))
            self._sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Lanzar hilos daemon
            for target, name in [(self._bucle_recepcion, "Receptor-TCP"), (self._bucle_heartbeat, "Heartbeat-UDP")]:
                threading.Thread(target=target, name=name, daemon=True).start()

            print(f"\n[SISTEMA] Conectado como '{self.usuario}'. Canal: {self.canal_actual}")
            print("[SISTEMA] Escribe /ayuda para ver comandos.\n")
            return True

        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            print(f"\n[ERROR] No se pudo conectar a {self.host}:{self.puerto_tcp}: {e}")
            if self._sock_tcp:
                try: self._sock_tcp.close()
                except OSError: pass
                self._sock_tcp = None
            return False

    def desconectar(self) -> None:
        self._conectado = False
        for s in (self._sock_tcp, self._sock_udp):
            if s:
                try: s.close()
                except OSError: pass
        self._sock_tcp = self._sock_udp = None

    def _enviar_tcp(self, datos: dict[str, Any]) -> None:
        """Helper: envía por TCP o desconecta si falla."""
        if not self._sock_tcp or not self._conectado:
            print("[AVISO] Sin conexión activa.")
            return
        try:
            enviar_mensaje_tcp(self._sock_tcp, datos)
        except ConexionCerradaError:
            print("\n[DESCONEXIÓN] Se perdió la conexión.")
            self.desconectar()

    # Métodos de envío
    def enviar_mensaje_canal(self, canal: str, texto: str) -> None:
        self._enviar_tcp({"tipo": TIPO_MENSAJE_CANAL, "canal": canal, "texto": texto})

    def enviar_mensaje_privado(self, dest: str, texto: str) -> None:
        self._enviar_tcp({"tipo": TIPO_MENSAJE_PRIVADO, "destinatario": dest, "texto": texto})

    def unirse_a_canal(self, canal: str) -> None:
        self._enviar_tcp({"tipo": TIPO_UNIR_CANAL, "canal": canal})

    def salir_de_canal(self, canal: str) -> None:
        self._enviar_tcp({"tipo": TIPO_SALIR_CANAL, "canal": canal})

    def solicitar_lista_canales(self) -> None:
        self._enviar_tcp({"tipo": TIPO_LISTAR_CANALES})

    def solicitar_lista_usuarios(self) -> None:
        self._enviar_tcp({"tipo": TIPO_LISTAR_USUARIOS})

    # --- Hilos de fondo ---
    def _bucle_recepcion(self) -> None:
        while self._conectado and self._sock_tcp:
            try:
                self._mostrar_mensaje(recibir_mensaje_tcp(self._sock_tcp))
            except TramaInvalidaError as e:
                print(f"\n[AVISO] Trama corrupta descartada: {e}")
            except ConexionCerradaError:
                if self._conectado:
                    print("\n[DESCONEXIÓN] El servidor cerró la conexión.")
                    self.desconectar()
                break

    def _mostrar_mensaje(self, msg: dict[str, Any]) -> None:
        """Formatea y muestra mensajes recibidos."""
        tipo = msg.get("tipo")
        hora = formatear_hora_corta(str(msg.get("timestamp", "")))

        if tipo == TIPO_DIFUSION_CANAL:
            print(f"\n[{hora}] [{msg.get('canal')}] <{msg.get('emisor')}>: {msg.get('texto')}")

        elif tipo == TIPO_DIFUSION_PRIVADA:
            emisor = msg.get("emisor")
            if emisor == self.usuario:
                print(f"\n[{hora}] [PRIVADO -> {msg.get('destinatario')}]: {msg.get('texto')}")
            else:
                print(f"\n[{hora}] [PRIVADO de {emisor}]: {msg.get('texto')}")

        elif tipo == TIPO_NOTIFICACION_SISTEMA:
            canales = msg.get("canales")
            if canales is not None:
                self.mis_canales = set(canales)
            tag = f" [{msg.get('canal')}]" if msg.get("canal") else ""
            print(f"\n[SISTEMA{tag}]: {msg.get('mensaje')}")

        elif tipo == TIPO_RESPUESTA_CANALES:
            self.mis_canales = set(msg.get("mis_canales", []))
            print("\n--- CANALES ---")
            for c in msg.get("canales_disponibles", []):
                marca = "✓" if c in self.mis_canales else " "
                activo = " -> ACTIVO" if c == self.canal_actual else ""
                print(f"  {c:<15} [{marca}]{activo}")
            print("---------------")

        elif tipo == TIPO_RESPUESTA_USUARIOS:
            print("\n--- OPERARIOS CONECTADOS ---")
            for u in msg.get("usuarios", []):
                print(f"  * {u.get('nombre',''):<15} [{u.get('estado','?').upper():<8}] "
                      f"(hace {u.get('segundos_desde_actividad',0)}s) {', '.join(u.get('canales',[]))}")
            print("----------------------------")

        elif tipo == TIPO_ERROR:
            print(f"\n[ERROR]: {msg.get('mensaje', 'Error del servidor')}")
        else:
            return

        self._prompt()

    def _bucle_heartbeat(self) -> None:
        while self._conectado:
            if self._sock_udp:
                try:
                    enviar_mensaje_udp(self._sock_udp, {"tipo": TIPO_HEARTBEAT, "usuario": self.usuario,
                                                         "timestamp": time.time()}, (self.host, self.puerto_udp))
                except Exception:
                    pass
            time.sleep(INTERVALO_HEARTBEAT_SEGUNDOS)

    def _prompt(self) -> None:
        sys.stdout.write(f"[{self.canal_actual}] > ")
        sys.stdout.flush()

    # --- Consola interactiva ---
    def ejecutar_consola(self) -> None:
        if not self._conectado:
            print("[ERROR] Debe conectarse primero.")
            return
        while self._conectado:
            try:
                self._prompt()
                linea = input().strip()
                if not linea:
                    continue
                if linea.startswith("/"):
                    self._comando(linea)
                else:
                    if self.canal_actual not in self.mis_canales:
                        print(f"[AVISO] No perteneces a {self.canal_actual}. Usa /unir {self.canal_actual}")
                        continue
                    self.enviar_mensaje_canal(self.canal_actual, linea)
            except (KeyboardInterrupt, EOFError):
                print("\n[SISTEMA] Cerrando sesión...")
                break
        self.desconectar()
        print("[SISTEMA] Sesión finalizada.")

    def _comando(self, linea: str) -> None:
        """Procesa comandos / con despacho declarativo."""
        partes = linea.split(" ", 2)
        cmd = partes[0].lower()

        # Declarativo: mapeo de comandos sin argumentos a funciones
        cmds_sin_args = {
            "/ayuda": self._ayuda, "/help": self._ayuda,
            "/canales": self.solicitar_lista_canales, "/channels": self.solicitar_lista_canales,
            "/usuarios": self.solicitar_lista_usuarios, "/who": self.solicitar_lista_usuarios,
            "/quien": self.solicitar_lista_usuarios,
            "/desconectar": self.desconectar, "/salir": self.desconectar,
            "/exit": self.desconectar, "/quit": self.desconectar,
        }

        if cmd in cmds_sin_args:
            cmds_sin_args[cmd]()
        elif cmd in ("/canal", "/c"):
            if len(partes) < 2:
                print(f"[USO] /canal <#canal>. Actual: {self.canal_actual}")
            else:
                c = partes[1].strip().lower()
                self.canal_actual = c if c.startswith("#") else f"#{c}"
                print(f"[SISTEMA] Canal activo: {self.canal_actual}")
        elif cmd in ("/unir", "/join"):
            if len(partes) < 2: print("[USO] /unir <#canal>")
            else: self.unirse_a_canal(partes[1])
        elif cmd in ("/salir_canal", "/leave"):
            if len(partes) < 2: print("[USO] /salir_canal <#canal>")
            else: self.salir_de_canal(partes[1])
        elif cmd in ("/msg", "/privado", "/p"):
            if len(partes) < 3: print("[USO] /msg <usuario> <mensaje>")
            else: self.enviar_mensaje_privado(partes[1], partes[2])
        else:
            print(f"[AVISO] Comando desconocido: '{cmd}'. Escribe /ayuda")

    def _ayuda(self) -> None:
        print("""
=== COMANDOS ===
  /canal <#canal>           Cambia canal activo
  /unir <#canal>            Unirse a un canal
  /salir_canal <#canal>     Salir de un canal
  /canales                  Lista canales
  /usuarios                 Lista operarios conectados
  /msg <usuario> <mensaje>  Mensaje privado
  /ayuda                    Este menú
  /salir                    Desconectar
================
""")


if __name__ == "__main__":
    usuario = sys.argv[1] if len(sys.argv) > 1 else input("Nombre de usuario / operario: ").strip()
    if not usuario:
        print("[ERROR] Nombre de usuario requerido.")
        sys.exit(1)
    cliente = ClienteMensajeria(usuario)
    if cliente.conectar():
        cliente.ejecutar_consola()

