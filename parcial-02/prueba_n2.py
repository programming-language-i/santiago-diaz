"""
PARCIAL 2 · Prueba del Nivel 2 (servidor concurrente). NO se modifica.

    python3 prueba_n2.py          desde la carpeta parcial2/

Primero usa RegistroClientes directamente. Después arranca
`python3 -m mensajeria.servidor <puerto>` en un puerto libre, le conecta varios
clientes y lo detiene al terminar: no hay que tener nada corriendo. Los
clientes de la prueba usan su protocolo.py, así que el Nivel 1 va primero.
Se detiene en el primer paso que falla y dice qué pasó.

Salida esperada cuando el nivel está resuelto:

    NIVEL 2 · Servidor concurrente
      [1/5] registro: insertar, buscar, borrar y destinatarios ... ok
      [2/5] varios clientes conectados a la vez .................. ok
      [3/5] dos clientes piden el mismo nombre a la vez .......... ok
      [4/5] retransmisión a los demás y no al emisor ............. ok
      [5/5] un cliente cerrado a la fuerza ....................... ok
    NIVEL 2: CORRECTO
"""
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

NIVEL = 2
TITULO = "Servidor concurrente"
MODULO = "mensajeria.servidor"

try:
    from mensajeria.protocolo import enviar_mensaje, recibir_mensaje
    from mensajeria.registro import RegistroClientes
except Exception:
    traceback.print_exc()
    print(f"NIVEL {NIVEL}: INCOMPLETO (mensajeria/ no se puede importar)")
    sys.exit(1)

HOST = "127.0.0.1"
ESPERA = 3              # segundos que un cliente espera una respuesta
ARRANQUE = 5            # segundos que se le dan al servidor para empezar a escuchar
PAUSA = 0.1             # ver DictLento
RAIZ = Path(__file__).resolve().parent


class Falla(Exception):
    """Lo que se observó no es lo que pide el enunciado."""


def corto(valor: object) -> str:
    texto = repr(valor)
    return texto if len(texto) <= 70 else texto[:67] + "..."


def donde(error: BaseException) -> str:
    """El error y la línea de mensajeria/ en la que saltó."""
    texto = f"{type(error).__name__}: {error}"
    for marco in reversed(traceback.extract_tb(error.__traceback__)):
        if Path(marco.filename).resolve().parent == RAIZ / "mensajeria":
            return f"{texto}\n(mensajeria/{Path(marco.filename).name}, línea {marco.lineno}: {marco.line})"
    return texto


# --- el servidor, en otro proceso -----------------------------------------

class Servidor:
    """Arranca el módulo del servidor en un puerto libre y guarda lo que imprime."""

    def __init__(self) -> None:
        self.proceso: subprocess.Popen | None = None
        self.puerto = 0
        self.impreso = tempfile.TemporaryFile()

    def arrancar(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonda:
            sonda.bind((HOST, 0))                   # puerto 0: el sistema elige uno libre
            self.puerto = sonda.getsockname()[1]
        entorno = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8:replace")
        self.proceso = subprocess.Popen(
            [sys.executable, "-m", MODULO, str(self.puerto)], cwd=RAIZ, env=entorno,
            stdin=subprocess.DEVNULL, stdout=self.impreso, stderr=subprocess.STDOUT)

    def vivo(self) -> bool:
        return self.proceso is not None and self.proceso.poll() is None

    def detener(self) -> None:
        if self.proceso is not None and self.proceso.poll() is None:
            self.proceso.terminate()
            try:
                self.proceso.wait(2)
            except subprocess.TimeoutExpired:
                self.proceso.kill()

    def ultimas_lineas(self, cuantas: int = 15) -> list[str]:
        time.sleep(0.3)                             # que termine de escribir, si está en eso
        self.impreso.seek(0)
        return self.impreso.read().decode("utf-8", errors="replace").splitlines()[-cuantas:]


servidor = Servidor()


# --- los clientes de la prueba --------------------------------------------

class Cliente:
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.sock = self._conectar()

    def _conectar(self) -> socket.socket:
        limite = time.monotonic() + ARRANQUE
        while True:
            try:
                return socket.create_connection((HOST, servidor.puerto), timeout=ESPERA)
            except OSError:
                if not servidor.vivo():
                    raise Falla("el servidor terminó solo.") from None
                if time.monotonic() > limite:
                    raise Falla(f"el servidor no acepta conexiones después de {ARRANQUE} s.") from None
                time.sleep(0.05)

    def enviar(self, texto: str) -> None:
        try:
            enviar_mensaje(self.sock, texto)
        except OSError as error:
            raise Falla(f"{self.nombre} no pudo enviar: el servidor cerró su conexión ({error}).") from None

    def recibir(self, que: str) -> str | None:
        """La siguiente trama que le llega a este cliente; None si el servidor cerró."""
        try:
            return recibir_mensaje(self.sock)
        except TimeoutError:
            raise Falla(f"{self.nombre} esperaba {que} y no llegó nada en {ESPERA} s.") from None
        except ConnectionError:
            return None

    def saludar(self) -> str | None:
        self.enviar(self.nombre)                    # la primera trama es el nombre
        return self.recibir("la respuesta a su nombre")

    def esperar(self, esperado: str) -> None:
        recibido = self.recibir(repr(esperado))
        if recibido is None:
            raise Falla(f"{self.nombre} esperaba {esperado!r} y el servidor le cerró la conexión.")
        if recibido != esperado:
            pista = ""
            if recibido.startswith(f"{self.nombre}: "):
                pista = "\nEs su propio mensaje: no se retransmite al emisor."
            raise Falla(f"{self.nombre} esperaba {esperado!r}\ny recibió {corto(recibido)}.{pista}")

    def cerrar(self) -> None:
        self.sock.close()

    def cerrar_a_la_fuerza(self) -> None:
        """Cierra sin despedirse: el servidor ve un reinicio de la conexión, no un cierre limpio."""
        formato = "hh" if os.name == "nt" else "ii"
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack(formato, 1, 0))
        self.sock.close()


clientes: dict[str, Cliente] = {}


def difundir(emisor: str, texto: str, receptores: tuple[str, ...]) -> None:
    clientes[emisor].enviar(texto)
    for nombre in receptores:
        clientes[nombre].esperar(f"{emisor}: {texto}")


def reingresar(nombre: str, motivo: str) -> Cliente:
    """Se conecta otra vez con un nombre que acaba de quedar libre."""
    limite = time.monotonic() + ESPERA
    while True:
        cliente = Cliente(nombre)
        respuesta = cliente.saludar()
        if respuesta == "OK":
            return cliente
        cliente.cerrar()
        if respuesta != "ERROR: nombre en uso":
            raise Falla(f"{nombre} volvió a conectarse y el servidor respondió {corto(respuesta)}.")
        if time.monotonic() > limite:
            raise Falla(f"{nombre} {motivo} y, {ESPERA} s después, su nombre sigue en uso.\n"
                        "Su entrada no se borró del registro: la limpieza va en un finally.")
        time.sleep(0.1)


# --- paso 1: el registro, sin red -----------------------------------------

class DictLento(dict):
    """Un dict que se demora al responder si una clave está.

    Entre "¿está el nombre?" e "insertarlo" normalmente pasan microsegundos y
    la carrera casi nunca se ve. Con esta demora, dos hilos que no comparten
    el lock se cruzan siempre. Con el lock bien puesto no cambia nada.
    """

    def __contains__(self, clave: object) -> bool:
        esta = super().__contains__(clave)
        time.sleep(PAUSA)
        return esta

    def __getitem__(self, clave):
        try:
            return super().__getitem__(clave)
        finally:
            time.sleep(PAUSA)

    def get(self, clave, defecto=None):
        valor = super().get(clave, defecto)
        time.sleep(PAUSA)
        return valor

    def keys(self):
        claves = list(super().keys())
        time.sleep(PAUSA)
        return claves

    def __iter__(self):
        claves = list(super().keys())
        time.sleep(PAUSA)
        return iter(claves)


def comprobar(obtenido: object, esperado: object, llamada: str) -> None:
    if obtenido is not esperado:
        raise Falla(f"{llamada} devolvió {corto(obtenido)}; se esperaba {esperado!r}.")


def registro_directo() -> None:
    ana, luis, sara = (socket.socket() for _ in range(3))      # tres conexiones cualesquiera
    with ana, luis, sara:
        registro = RegistroClientes()
        comprobar(registro.insertar("ana", ana), True, 'insertar("ana", c1) en un registro vacío')
        comprobar(registro.insertar("ana", luis), False, 'insertar("ana", c2) con ana ya registrada')
        comprobar(registro.buscar("ana"), ana, 'después del insertar rechazado, buscar("ana")')
        comprobar(registro.buscar("luis"), None, 'buscar("luis") sin luis registrado')
        comprobar(registro.insertar("luis", luis), True, 'insertar("luis", c2)')

        obtenido = registro.destinatarios(excepto="ana")
        if not isinstance(obtenido, list) or obtenido != [("luis", luis)]:
            raise Falla(f'con ana y luis registrados, destinatarios(excepto="ana") devolvió\n{corto(obtenido)}\n'
                        'y se esperaba la lista [("luis", c2)].')
        copia = registro.destinatarios(excepto="nadie")
        registro.insertar("sara", sara)
        if len(copia) != 2:
            raise Falla("la lista que devolvió destinatarios cambió al insertar a otro cliente.\n"
                        "Debe ser una copia, hecha dentro del lock.")

        registro.borrar("luis")
        comprobar(registro.buscar("luis"), None, 'después de borrar("luis"), buscar("luis")')
        try:
            registro.borrar("luis")
        except KeyError:
            raise Falla('borrar("luis") por segunda vez lanzó KeyError.\n'
                        "Borrar un nombre que ya no está no es un error: en el servidor pasa.") from None

    # Dos hilos piden el mismo nombre en el mismo instante.
    registro = RegistroClientes()
    try:
        for atributo, valor in list(vars(registro).items()):
            if type(valor) is dict:
                setattr(registro, atributo, DictLento(valor))
    except TypeError:
        pass
    barrera = threading.Barrier(2)
    resultados: list[object] = []
    errores: list[str] = []

    def pedir_nombre() -> None:
        try:
            barrera.wait(ESPERA)
            resultados.append(registro.insertar("ana", ana))
        except Exception as error:
            errores.append(donde(error))

    hilos = [threading.Thread(target=pedir_nombre, daemon=True) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(ESPERA)
    if errores:
        raise Falla("dos hilos llamaron a insertar a la vez: " + errores[0])
    if len(resultados) < 2:
        raise Falla(f"dos hilos llamaron a insertar a la vez y no terminaron en {ESPERA} s.\n"
                    "¿Un lock que se toma y no se suelta?")
    if resultados == [True, True]:
        raise Falla("dos hilos insertaron el mismo nombre a la vez y los dos recibieron True.\n"
                    "Entre verificar si el nombre está e insertarlo se coló el otro hilo:\n"
                    "las dos cosas van bajo el MISMO lock.")
    if sorted(resultados, key=repr) != [False, True]:
        raise Falla(f"dos hilos insertaron el mismo nombre a la vez y recibieron {resultados};\n"
                    "se esperaba un True y un False.")


# --- pasos 2 a 5: el servidor, por la red ---------------------------------

def varios_a_la_vez() -> None:
    servidor.arrancar()
    clientes["mudo"] = Cliente("mudo")              # se conecta y nunca dice su nombre
    for nombre in ("ana", "luis", "sara"):          # cuatro conexiones abiertas a la vez
        clientes[nombre] = Cliente(nombre)
    for nombre in ("sara", "luis", "ana"):
        try:
            respuesta = clientes[nombre].saludar()
        except Falla as falla:
            raise Falla(f"{falla}\nHay cuatro clientes conectados y uno todavía no ha dicho su nombre:\n"
                        "¿cada conexión tiene su propio hilo?") from None
        if respuesta != "OK":
            raise Falla(f'{nombre} envió su nombre y el servidor respondió {corto(respuesta)}; se esperaba "OK".')


def mismo_nombre() -> None:
    rivales = [Cliente("pedro"), Cliente("pedro")]  # los dos ya conectados
    barrera = threading.Barrier(2)
    respuestas: list[object] = [None, None]

    def pedir_nombre(i: int) -> None:
        try:
            barrera.wait(ESPERA)
            respuestas[i] = rivales[i].saludar()
        except Exception as error:
            respuestas[i] = error

    hilos = [threading.Thread(target=pedir_nombre, args=(i,), daemon=True) for i in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(ESPERA + 2)
    for respuesta in respuestas:
        if isinstance(respuesta, Exception):
            raise respuesta
    if respuestas == ["OK", "OK"]:
        raise Falla('los dos recibieron "OK": quedaron dos clientes con el mismo nombre.')
    if sorted(respuestas, key=repr) != ["ERROR: nombre en uso", "OK"]:
        raise Falla(f"el servidor respondió {corto(respuestas[0])} y {corto(respuestas[1])};\n"
                    'se esperaba un "OK" y un "ERROR: nombre en uso".')

    ganador, perdedor = rivales if respuestas[0] == "OK" else reversed(rivales)
    try:
        sobra = perdedor.recibir("que el servidor cerrara su conexión")
    except Falla:
        raise Falla('el servidor respondió "ERROR: nombre en uso" y dejó abierta esa conexión:\n'
                    "debe cerrarla.") from None
    if sobra is not None:
        raise Falla(f'después de "ERROR: nombre en uso" el servidor envió {corto(sobra)}; debía cerrar la conexión.')
    perdedor.cerrar()

    tercero = Cliente("pedro")
    respuesta = tercero.saludar()
    tercero.cerrar()
    if respuesta != "ERROR: nombre en uso":
        raise Falla(f"pedro sigue conectado, otro cliente pidió su nombre y el servidor respondió {corto(respuesta)}.\n"
                    "¿Al rechazar al repetido se borró del registro la entrada del que sí entró?")
    clientes["pedro"] = ganador


def retransmision() -> None:
    difundir("ana", "camión 3 listo", ("luis", "sara", "pedro"))
    difundir("luis", "muelle 2 libre, ¿quién entra?", ("ana", "sara", "pedro"))


def cierre_a_la_fuerza() -> None:
    clientes["sara"].cerrar_a_la_fuerza()
    clientes["sara"] = reingresar("sara", "se desconectó a la fuerza")
    difundir("ana", "¿siguen ahí?", ("luis", "pedro", "sara"))

    clientes["luis"].cerrar()                       # y uno que se va con aviso
    clientes["luis"] = reingresar("luis", "cerró su conexión")
    difundir("pedro", "turno de noche", ("ana", "sara", "luis"))
    if not servidor.vivo():
        raise Falla("el servidor terminó solo.")


PASOS = [
    ("registro: insertar, buscar, borrar y destinatarios", registro_directo, 15),
    ("varios clientes conectados a la vez", varios_a_la_vez, 30),
    ("dos clientes piden el mismo nombre a la vez", mismo_nombre, 30),
    ("retransmisión a los demás y no al emisor", retransmision, 30),
    ("un cliente cerrado a la fuerza", cierre_a_la_fuerza, 30),
]


# --- ejecución ------------------------------------------------------------

def ejecutar(funcion, limite: int) -> str | None:
    """None si el paso pasó; si no, el texto de lo que falló."""
    resultado: list[str | None] = []

    def tarea() -> None:
        try:
            funcion()
            resultado.append(None)
        except Falla as falla:
            resultado.append(str(falla))
        except Exception as error:
            resultado.append(donde(error))

    hilo = threading.Thread(target=tarea, daemon=True)
    hilo.start()
    hilo.join(limite)                               # un servidor colgado no cuelga la prueba
    if not resultado:
        return f"no terminó en {limite} s."
    return resultado[0]


def protocolo_listo() -> None:
    """Un mensaje de ida y vuelta con protocolo.py: sin eso la prueba no puede hablar con el servidor."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as oyente:
        oyente.bind((HOST, 0))
        oyente.listen(1)
        with socket.create_connection(oyente.getsockname(), timeout=ESPERA) as emisor:
            receptor, _ = oyente.accept()
            with receptor:
                receptor.settimeout(ESPERA)
                enviar_mensaje(emisor, "año")
                if recibir_mensaje(receptor) != "año":
                    raise Falla("")


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    print(f"NIVEL {NIVEL} · {TITULO}")
    if ejecutar(protocolo_listo, 5) is not None:
        print("  mensajeria/protocolo.py todavía no lleva un mensaje de ida y vuelta.")
        print("  Termine primero el Nivel 1:  python3 prueba_n1.py")
        print(f"NIVEL {NIVEL}: INCOMPLETO (falta el Nivel 1)")
        return 1
    try:
        for i, (titulo, funcion, limite) in enumerate(PASOS, 1):
            print(f"  [{i}/{len(PASOS)}] {titulo} ".ljust(62, ".") + " ", end="", flush=True)
            falla = ejecutar(funcion, limite)
            if falla is None:
                print("ok")
                continue
            print("FALLA")
            for linea in falla.splitlines():
                print("        " + linea)
            impreso = servidor.ultimas_lineas()
            if impreso:
                print("        --- lo último que imprimió el servidor ---")
                for linea in impreso:
                    print("        " + linea)
            print(f"NIVEL {NIVEL}: INCOMPLETO (falla el paso {i} de {len(PASOS)})")
            return 1
        print(f"NIVEL {NIVEL}: CORRECTO")
        return 0
    finally:
        servidor.detener()


if __name__ == "__main__":
    codigo = main()
    sys.stdout.flush()
    sys.exit(codigo)
