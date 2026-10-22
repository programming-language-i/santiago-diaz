"""
PARCIAL 2 · Prueba del Nivel 1 (framing). NO se modifica.

    python3 prueba_n1.py          desde la carpeta parcial2/

Conecta dos sockets por localhost y usa las funciones de mensajeria/protocolo.py
en los dos extremos. No necesita ningún servidor corriendo. Se detiene en el
primer paso que falla y dice qué pasó.

Salida esperada cuando el nivel está resuelto:

    NIVEL 1 · Framing
      [1/4] ráfaga de 1000 mensajes cortos sin pausa ............. ok
      [2/4] un mensaje de 3 MB ................................... ok
      [3/4] un mensaje con ñ y emoji ............................. ok
      [4/4] cierre limpio del otro extremo ....................... ok
    NIVEL 1: CORRECTO
"""
import socket
import sys
import threading
import traceback
from pathlib import Path

try:
    from mensajeria.protocolo import enviar_mensaje, recibir_mensaje
except Exception:
    traceback.print_exc()
    print("NIVEL 1: INCOMPLETO (mensajeria/protocolo.py no se puede importar)")
    sys.exit(1)

HOST = "127.0.0.1"
ESPERA = 5              # segundos que se espera cada lectura
CARPETA = Path(__file__).resolve().parent / "mensajeria"


class Falla(Exception):
    """Lo que se observó no es lo que pide el enunciado."""


# --- apoyo ----------------------------------------------------------------

def par(bufer_de_recepcion: int | None = None) -> tuple[socket.socket, socket.socket]:
    """Dos sockets TCP conectados entre sí: lo que se envía por uno llega al otro."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as oyente:
        oyente.bind((HOST, 0))                      # puerto 0: el sistema elige uno libre
        oyente.listen(1)
        receptor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if bufer_de_recepcion:
            receptor.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, bufer_de_recepcion)
        receptor.connect(oyente.getsockname())
        emisor, _ = oyente.accept()
    emisor.settimeout(ESPERA)
    receptor.settimeout(ESPERA)
    return emisor, receptor


def donde(error: BaseException) -> str:
    """El error y la línea de mensajeria/ en la que saltó."""
    texto = f"{type(error).__name__}: {error}"
    for marco in reversed(traceback.extract_tb(error.__traceback__)):
        if Path(marco.filename).resolve().parent == CARPETA:
            return f"{texto}\n(mensajeria/{Path(marco.filename).name}, línea {marco.lineno}: {marco.line})"
    return texto


def en_hilo(funcion) -> tuple[threading.Thread, list[str]]:
    """Corre funcion() en otro hilo y guarda el error, si lo hay."""
    errores: list[str] = []

    def tarea() -> None:
        try:
            funcion()
        except Exception as error:
            errores.append("al enviar, " + donde(error))

    hilo = threading.Thread(target=tarea, daemon=True)
    hilo.start()
    return hilo, errores


def recibir(receptor: socket.socket, errores_del_emisor: list[str]) -> str | None:
    try:
        return recibir_mensaje(receptor)
    except TimeoutError:
        if errores_del_emisor:
            raise Falla(errores_del_emisor[0]) from None
        raise Falla(f"recibir_mensaje esperó {ESPERA} s y no llegó el mensaje completo.") from None


def corto(valor: object) -> str:
    texto = repr(valor)
    return texto if len(texto) <= 60 else texto[:57] + "..."


# --- los cuatro pasos -----------------------------------------------------

def rafaga() -> None:
    emisor, receptor = par()
    with emisor, receptor:
        mensajes = [f"mensaje {i}" for i in range(1, 1001)]

        def enviar_todos() -> None:
            for mensaje in mensajes:
                enviar_mensaje(emisor, mensaje)

        hilo, errores = en_hilo(enviar_todos)
        hilo.join(ESPERA)                           # los 1000 salen antes de leer el primero
        for i, esperado in enumerate(mensajes, 1):
            recibido = recibir(receptor, errores)
            if errores:
                raise Falla(errores[0])
            if recibido is None:
                raise Falla(f"en el mensaje {i} de 1000, recibir_mensaje devolvió None.")
            if recibido != esperado:
                raise Falla(f"el mensaje {i} de 1000 llegó como {corto(recibido)} y se envió {esperado!r}.\n"
                            "Los mensajes llegan pegados o partidos: cada recibir_mensaje debe leer\n"
                            "el prefijo y después exactamente los bytes que dice.")


def mensaje_grande() -> None:
    # Con un búfer de recepción pequeño, un recv() no puede traer los 3 MB de una vez.
    emisor, receptor = par(bufer_de_recepcion=65536)
    with emisor, receptor:
        grande = "0123456789" * 300_000             # 3 000 000 bytes

        def enviar_dos() -> None:
            enviar_mensaje(emisor, grande)
            enviar_mensaje(emisor, "fin del grande")

        hilo, errores = en_hilo(enviar_dos)
        recibido = recibir(receptor, errores)
        if recibido is None:
            raise Falla(errores[0] if errores else "recibir_mensaje devolvió None.")
        if len(recibido) < len(grande):
            raise Falla(f"se enviaron {len(grande)} bytes y recibir_mensaje devolvió {len(recibido)}.\n"
                        "recv(n) entrega lo que haya llegado, no los n bytes: recibir_exacto debe\n"
                        "llamarlo en bucle hasta completarlos.")
        if recibido != grande:
            raise Falla("el mensaje de 3 MB llegó con otro contenido.")
        siguiente = recibir(receptor, errores)
        if siguiente != "fin del grande":
            raise Falla(f"después del mensaje de 3 MB llegó {corto(siguiente)}: el flujo quedó desincronizado.")
        hilo.join(ESPERA)


def enie_y_emoji() -> None:
    texto = "mañana llega el camión 🚚"
    cuerpo = texto.encode("utf-8")
    trama = len(cuerpo).to_bytes(4, "big") + cuerpo     # lo que debe viajar por el cable

    # 1. Lo que escribe enviar_mensaje, byte por byte.
    emisor, receptor = par()
    with emisor, receptor:
        enviar_mensaje(emisor, texto)
        emisor.close()
        with receptor.makefile("rb") as lector:
            enviado = lector.read()
    if enviado != trama:
        if len(enviado) < 4:
            raise Falla(f"enviar_mensaje envió {len(enviado)} bytes: falta el prefijo de 4 bytes.")
        prefijo = int.from_bytes(enviado[:4], "big")
        if prefijo == len(texto):
            raise Falla(f"el prefijo dice {prefijo} y el cuerpo ocupa {len(cuerpo)} bytes.\n"
                        f"{prefijo} es la cantidad de caracteres: la ñ, la ó y el emoji ocupan más\n"
                        "de un byte. La longitud se toma del texto YA codificado.")
        if int.from_bytes(enviado[:4], "little") == len(cuerpo):
            raise Falla('el prefijo no va en big-endian: es struct.pack("!I", n), con el signo !.')
        if enviado[4:] != cuerpo:
            raise Falla("el cuerpo que se envió no es el texto codificado en UTF-8.")
        raise Falla(f"el prefijo dice {prefijo} y el cuerpo ocupa {len(cuerpo)} bytes.")

    # 2. Lo que entiende recibir_mensaje cuando le llega esa trama, y la siguiente.
    emisor, receptor = par()
    with emisor, receptor:
        emisor.sendall(trama + trama)
        for cual in ("primer", "segundo"):
            recibido = recibir(receptor, [])
            if recibido != texto:
                raise Falla(f"se envió dos veces {texto!r}\ny el {cual} recibir_mensaje devolvió {corto(recibido)}.")


def cierre_limpio() -> None:
    casos = [
        ("sin enviar nada", b""),
        ("con el prefijo a medias", b"\x00\x00"),
        ("a mitad de un mensaje", (100).to_bytes(4, "big") + b"solo diez."),
    ]
    for cuando, enviado in casos:
        emisor, receptor = par()
        with emisor, receptor:
            emisor.sendall(enviado)
            emisor.close()
            recibido = recibir(receptor, [])
            if recibido is not None:
                raise Falla(f"el otro extremo cerró {cuando} y recibir_mensaje devolvió {corto(recibido)}.\n"
                            "Debe devolver None.")


PASOS = [
    ("ráfaga de 1000 mensajes cortos sin pausa", rafaga, 30),
    ("un mensaje de 3 MB", mensaje_grande, 30),
    ("un mensaje con ñ y emoji", enie_y_emoji, 15),
    ("cierre limpio del otro extremo", cierre_limpio, 5),
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
    hilo.join(limite)                               # un bucle infinito no cuelga la prueba
    if not resultado:
        return (f"no terminó en {limite} s. ¿Un bucle que no acaba?\n"
                'Cuando el otro extremo cierra, recv() devuelve b"" una y otra vez.')
    return resultado[0]


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    print("NIVEL 1 · Framing")
    for i, (titulo, funcion, limite) in enumerate(PASOS, 1):
        print(f"  [{i}/{len(PASOS)}] {titulo} ".ljust(62, ".") + " ", end="", flush=True)
        falla = ejecutar(funcion, limite)
        if falla is not None:
            print("FALLA")
            for linea in falla.splitlines():
                print("        " + linea)
            print(f"NIVEL 1: INCOMPLETO (falla el paso {i} de {len(PASOS)})")
            return 1
        print("ok")
    print("NIVEL 1: CORRECTO")
    return 0


if __name__ == "__main__":
    codigo = main()
    sys.stdout.flush()
    sys.exit(codigo)
