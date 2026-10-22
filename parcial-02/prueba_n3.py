"""
PARCIAL 2 · Prueba del Nivel 3 (mensajes JSON). NO se modifica.

    python3 prueba_n3.py          desde la carpeta parcial2/

Arranca `python3 -m mensajeria.servidor_json <puerto>` en un puerto libre, le
conecta tres clientes (ana, luis y sara) y lo detiene al terminar: no hay que
tener nada corriendo. mensajeria/servidor_json.py lo crea usted, copiando su
servidor.py. Los clientes de la prueba usan su protocolo.py.
Se detiene en el primer paso que falla y dice qué pasó.

Salida esperada cuando el nivel está resuelto:

    NIVEL 3 · Mensajes JSON
      [1/5] un mensaje llega a los demás con emisor y timestamp .. ok
      [2/5] un privado llega solo a su destino ................... ok
      [3/5] un emisor falsificado llega con el nombre real ....... ok
      [4/5] los cuatro pedidos inválidos reciben un error ........ ok
      [5/5] un JSON dañado y después uno válido .................. ok
    NIVEL 3: CORRECTO
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

NIVEL = 3
TITULO = "Mensajes JSON"
MODULO = "mensajeria.servidor_json"

try:
    from mensajeria.protocolo import enviar_mensaje, recibir_mensaje
except Exception:
    traceback.print_exc()
    print(f"NIVEL {NIVEL}: INCOMPLETO (mensajeria/ no se puede importar)")
    sys.exit(1)

HOST = "127.0.0.1"
ESPERA = 3              # segundos que un cliente espera una respuesta
ARRANQUE = 5            # segundos que se le dan al servidor para empezar a escuchar
RAIZ = Path(__file__).resolve().parent


class Falla(Exception):
    """Lo que se observó no es lo que pide el enunciado."""


def corto(valor: object) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    return texto if len(texto) <= 150 else texto[:147] + "..."


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

    def pedir(self, pedido: dict[str, str]) -> None:
        self.enviar(json.dumps(pedido, ensure_ascii=False))

    def recibir(self, que: str) -> str:
        """La siguiente trama que le llega a este cliente."""
        try:
            texto = recibir_mensaje(self.sock)
        except TimeoutError:
            raise Falla(f"{self.nombre} esperaba {que} y no llegó nada en {ESPERA} s.") from None
        except ConnectionError:
            texto = None
        if texto is None:
            raise Falla(f"{self.nombre} esperaba {que} y el servidor le cerró la conexión.")
        return texto

    def recibir_json(self, que: str) -> dict:
        texto = self.recibir(que)
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            datos = None
        if not isinstance(datos, dict):
            raise Falla(f"{self.nombre} esperaba {que}\ny recibió algo que no es un objeto JSON: {corto(texto)}")
        return datos

    def esperar(self, esperado: dict[str, str], pista: str = "") -> None:
        """La siguiente trama debe traer estos campos, y un timestamp puesto por el servidor."""
        que = f"un {esperado['tipo']} de {esperado['emisor']}"
        recibido = self.recibir_json(que)
        for campo, valor in esperado.items():
            if recibido.get(campo) != valor:
                raise Falla(f"{self.nombre} esperaba {que}\ny recibió {corto(recibido)}\n"
                            f"El campo {campo!r} es {recibido.get(campo)!r} y debía ser {valor!r}.{pista}")
        problema = revisar_hora(recibido.get("timestamp"))
        if problema:
            raise Falla(f"{self.nombre} recibió {corto(recibido)}\n{problema}")

    def cerrar(self) -> None:
        self.sock.close()


def revisar_hora(valor: object) -> str:
    """Vacío si es la hora actual en ISO 8601 con segundos; si no, qué tiene de malo."""
    formato = 'datetime.now().isoformat(timespec="seconds")'
    if not isinstance(valor, str):
        return f"Falta el campo 'timestamp': lo pone el servidor con {formato}."
    try:
        hora = datetime.fromisoformat(valor)
    except ValueError:
        return f"El 'timestamp' {valor!r} no es una fecha ISO 8601: se arma con {formato}."
    if len(valor) != 19:
        return f"El 'timestamp' {valor!r} no va con segundos, como AAAA-MM-DDTHH:MM:SS: se arma con {formato}."
    if abs((datetime.now() - hora).total_seconds()) > 120:
        return f"El 'timestamp' {valor!r} no es la hora actual: lo pone el servidor, no el cliente."
    return ""


clientes: dict[str, Cliente] = {}
controles = 0


def nadie_mas_recibio(emisor: str, motivo: str) -> None:
    """Comprueba que a los otros dos no les llegó nada de más.

    `emisor` envía un mensaje de control: como las tramas llegan en orden, lo
    siguiente que reciba cada uno de los otros debe ser ese mensaje.
    """
    global controles
    controles += 1
    contenido = f"control {controles}"
    clientes[emisor].pedir({"tipo": "mensaje", "contenido": contenido})
    for nombre, cliente in clientes.items():
        if nombre == emisor:
            continue
        recibido = cliente.recibir_json(f"un mensaje de {emisor}")
        if recibido.get("tipo") != "mensaje" or recibido.get("contenido") != contenido:
            raise Falla(f"{nombre} recibió {corto(recibido)}\ny no debía recibirlo: {motivo}.")


# --- los cinco pasos ------------------------------------------------------

def mensaje_a_los_demas() -> None:
    servidor.arrancar()
    for nombre in ("ana", "luis", "sara"):
        clientes[nombre] = Cliente(nombre)
        clientes[nombre].enviar(nombre)             # el saludo no cambia: texto plano
        respuesta = clientes[nombre].recibir("la respuesta a su nombre")
        if respuesta != "OK":
            raise Falla(f'{nombre} envió su nombre y el servidor respondió {corto(respuesta)}; se esperaba "OK".')

    clientes["ana"].pedir({"tipo": "mensaje", "contenido": "camión 3 listo"})
    esperado = {"tipo": "mensaje", "emisor": "ana", "canal": "general", "contenido": "camión 3 listo"}
    clientes["luis"].esperar(esperado)
    clientes["sara"].esperar(esperado)
    nadie_mas_recibio("luis", "un mensaje no vuelve a quien lo envió")


def privado_solo_al_destino() -> None:
    clientes["ana"].pedir({"tipo": "privado", "destino": "luis", "contenido": "pasa por el muelle 2"})
    clientes["luis"].esperar({"tipo": "privado", "emisor": "ana", "destino": "luis",
                              "contenido": "pasa por el muelle 2"})
    nadie_mas_recibio("ana", "el privado era solo para luis")
    nadie_mas_recibio("luis", "el privado era solo para luis")


def emisor_falsificado() -> None:
    pista = "\nEl emisor lo pone el servidor con el nombre del registro: el que venga en el pedido se ignora."
    clientes["sara"].pedir({"tipo": "mensaje", "emisor": "ana", "timestamp": "1999-12-31T23:59:59",
                            "contenido": "todos a casa, lo digo yo"})
    esperado = {"tipo": "mensaje", "emisor": "sara", "canal": "general", "contenido": "todos a casa, lo digo yo"}
    clientes["ana"].esperar(esperado, pista)
    clientes["luis"].esperar(esperado, pista)

    clientes["sara"].pedir({"tipo": "privado", "emisor": "ana", "destino": "luis", "contenido": "de parte de ana"})
    clientes["luis"].esperar({"tipo": "privado", "emisor": "sara", "destino": "luis",
                              "contenido": "de parte de ana"}, pista)


def cuatro_errores() -> None:
    casos = [
        ("un privado para pedro, que no está conectado",
         {"tipo": "privado", "destino": "pedro", "contenido": "¿estás?"}),
        ("un privado para ella misma",
         {"tipo": "privado", "destino": "ana", "contenido": "nota para mí"}),
        ("un pedido con un tipo desconocido",
         {"tipo": "borrar", "contenido": "todo"}),
        ("un mensaje sin contenido",
         {"tipo": "mensaje"}),
    ]
    for que, pedido in casos:
        clientes["ana"].pedir(pedido)
        try:
            recibido = clientes["ana"].recibir_json("un error")
        except Falla as falla:
            raise Falla(f"ana envió {que}:\n{falla}") from None
        detalle = recibido.get("detalle")
        if recibido.get("tipo") != "error" or not isinstance(detalle, str) or not detalle:
            raise Falla(f"ana envió {que}\ny recibió {corto(recibido)}\n"
                        'Se esperaba {"tipo": "error", "detalle": "..."}.')
    nadie_mas_recibio("ana", "un pedido inválido no se reenvía y el error va solo a quien lo hizo")


def json_roto() -> None:
    clientes["luis"].enviar('{"tipo": "mensaje", "contenido": "se cortó la lla')
    clientes["luis"].pedir({"tipo": "mensaje", "contenido": "sigo aquí"})
    esperado = {"tipo": "mensaje", "emisor": "luis", "canal": "general", "contenido": "sigo aquí"}
    try:
        clientes["ana"].esperar(esperado)
        clientes["sara"].esperar(esperado)
    except Falla as falla:
        raise Falla(f"luis envió una trama con el JSON dañado y después un mensaje válido:\n{falla}\n"
                    "El JSON dañado se descarta y la conexión de luis sigue.") from None

    # A luis se le puede responder un error por la trama dañada, o nada: las dos cosas valen.
    global controles
    controles += 1
    clientes["sara"].pedir({"tipo": "mensaje", "contenido": f"control {controles}"})
    recibido = clientes["luis"].recibir_json("un mensaje de sara")
    if recibido.get("tipo") == "error":
        recibido = clientes["luis"].recibir_json("un mensaje de sara")
    if recibido.get("contenido") != f"control {controles}":
        raise Falla(f"después del JSON dañado, luis recibió {corto(recibido)}\ny no debía recibirlo.")
    clientes["ana"].recibir_json("un mensaje de sara")
    if not servidor.vivo():
        raise Falla("el servidor terminó solo.")


PASOS = [
    ("un mensaje llega a los demás con emisor y timestamp", mensaje_a_los_demas, 30),
    ("un privado llega solo a su destino", privado_solo_al_destino, 30),
    ("un emisor falsificado llega con el nombre real", emisor_falsificado, 30),
    ("los cuatro pedidos inválidos reciben un error", cuatro_errores, 30),
    ("un JSON dañado y después uno válido", json_roto, 30),
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
    if not (RAIZ / "mensajeria" / "servidor_json.py").exists():
        print("  No existe mensajeria/servidor_json.py.")
        print("  Copie mensajeria/servidor.py con ese nombre y trabaje sobre la copia.")
        print(f"NIVEL {NIVEL}: INCOMPLETO (falta mensajeria/servidor_json.py)")
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
