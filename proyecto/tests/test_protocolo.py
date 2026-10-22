"""Pruebas unitarias para protocolo y framing."""
import json, socket, struct, sys, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.protocolo import (
    ConexionCerradaError, TramaInvalidaError, codificar_trama_tcp,
    enviar_mensaje_tcp, enviar_mensaje_udp, recibir_mensaje_tcp, recibir_mensaje_udp,
)


class TestProtocolo(unittest.TestCase):

    def test_codificar_trama_prefijo_correcto(self) -> None:
        datos = {"tipo": "mensaje_canal", "texto": "Hola mundo"}
        trama = codificar_trama_tcp(datos)
        longitud = struct.unpack("!I", trama[:4])[0]
        payload = trama[4:]
        self.assertEqual(len(payload), longitud)
        self.assertEqual(json.loads(payload.decode("utf-8")), datos)

    def test_loopback_tcp(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        puerto = srv.getsockname()[1]
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.connect(("127.0.0.1", puerto))
        acc, _ = srv.accept()
        try:
            datos = {"tipo": "login", "usuario": "sergio", "turno": 1}
            enviar_mensaje_tcp(cli, datos)
            self.assertEqual(recibir_mensaje_tcp(acc), datos)
        finally:
            for s in [cli, acc, srv]:
                try: s.close()
                except OSError: pass

    def test_json_corrupto_lanza_trama_invalida(self) -> None:
        a, b = socket.socketpair()
        try:
            payload = b'{"tipo": "x", texto_sin_cerrar'
            a.sendall(struct.pack("!I", len(payload)) + payload)
            with self.assertRaises(TramaInvalidaError):
                recibir_mensaje_tcp(b)
        finally:
            a.close(); b.close()

    def test_desconexion_mitad_trama(self) -> None:
        a, b = socket.socketpair()
        try:
            a.sendall(struct.pack("!I", 100) + b"12345")
            a.close()
            with self.assertRaises(TramaInvalidaError):
                recibir_mensaje_tcp(b)
        finally:
            b.close()

    def test_desconexion_limpia(self) -> None:
        a, b = socket.socketpair()
        try:
            a.close()
            with self.assertRaises(ConexionCerradaError):
                recibir_mensaje_tcp(b)
        finally:
            b.close()

    def test_udp_loopback(self) -> None:
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.bind(("127.0.0.1", 0))
        puerto = rx.getsockname()[1]
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            datos = {"tipo": "heartbeat", "usuario": "sergio"}
            enviar_mensaje_udp(tx, datos, ("127.0.0.1", puerto))
            recibido, _ = recibir_mensaje_udp(rx)
            self.assertEqual(recibido, datos)
        finally:
            tx.close(); rx.close()


if __name__ == "__main__":
    unittest.main()
