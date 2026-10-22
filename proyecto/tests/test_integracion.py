import socket, struct, sys, tempfile, time, unittest
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.bitacora import BitacoraAuditable
from mensajeria.protocolo import enviar_mensaje_tcp, enviar_mensaje_udp, recibir_mensaje_tcp
from mensajeria.servidor import ServidorMensajeria


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TestIntegracion(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta_bit = Path(self.tmp.name) / "bitacora_test.jsonl"
        self.p_tcp, self.p_udp = _puerto_libre(), _puerto_libre()
        self.servidor = ServidorMensajeria("127.0.0.1", self.p_tcp, self.p_udp, self.ruta_bit)
        self.servidor.iniciar()
        time.sleep(0.05)

    def tearDown(self) -> None:
        self.servidor.detener()
        self.tmp.cleanup()

    def _login(self, nombre: str) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", self.p_tcp))
        enviar_mensaje_tcp(sock, {"tipo": "login", "usuario": nombre})
        resp = recibir_mensaje_tcp(sock)
        self.assertEqual(resp.get("tipo"), "login_exito")
        return sock

    def _esperar(self, sock: socket.socket, tipo: str, intentos: int = 6) -> dict[str, Any]:
        for _ in range(intentos):
            t = recibir_mensaje_tcp(sock)
            if t.get("tipo") == tipo:
                return t
        self.fail(f"No se recibió '{tipo}' en {intentos} intentos.")

    def test_tres_clientes_y_canal_general(self) -> None:
        c1, c2, c3 = self._login("op1"), self._login("op2"), self._login("op3")
        try:
            time.sleep(0.05)
            enviar_mensaje_tcp(c1, {"tipo": "mensaje_canal", "canal": "#general", "texto": "Aviso general"})
            for s in (c1, c2, c3):
                t = self._esperar(s, "difusion_canal")
                self.assertEqual(t.get("texto"), "Aviso general")
                self.assertEqual(t.get("emisor"), "op1")
                self.assertIn("timestamp", t)
                self.assertIn("id", t)
        finally:
            list(map(lambda s: s.close(), [c1, c2, c3]))

    def test_rechazo_duplicado(self) -> None:
        c1 = self._login("unico")
        c2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c2.connect(("127.0.0.1", self.p_tcp))
        try:
            enviar_mensaje_tcp(c2, {"tipo": "login", "usuario": "unico"})
            resp = recibir_mensaje_tcp(c2)
            self.assertEqual(resp.get("tipo"), "error")
            self.assertIn("Ya existe", resp.get("mensaje", ""))
        finally:
            c1.close(); c2.close()

    def test_mensaje_privado_req_12(self) -> None:
        em, rx, t3 = self._login("emisor"), self._login("receptor"), self._login("tercero")
        try:
            time.sleep(0.05)
            enviar_mensaje_tcp(em, {"tipo": "mensaje_privado", "destinatario": "receptor", "texto": "Confidencial"})
            tr = self._esperar(rx, "difusion_privada")
            self.assertEqual(tr.get("texto"), "Confidencial")
            self.assertEqual(tr.get("emisor"), "emisor")
            te = self._esperar(em, "difusion_privada")
            self.assertEqual(te.get("texto"), "Confidencial")
            # Verificar bitácora
            privados = [m for m in BitacoraAuditable(self.ruta_bit).iterar_mensajes() if m.get("tipo") == "difusion_privada"]
            self.assertEqual(len(privados), 1)
        finally:
            list(map(lambda s: s.close(), [em, rx, t3]))

    def test_tolerancia_desconexion_abrupta_req_04(self) -> None:
        c1, c2 = self._login("estable"), self._login("falla")
        try:
            c2.close()
            time.sleep(0.1)
            enviar_mensaje_tcp(c1, {"tipo": "mensaje_canal", "canal": "#general", "texto": "Sigo vivo"})
            self.assertEqual(self._esperar(c1, "difusion_canal").get("texto"), "Sigo vivo")
        finally:
            c1.close()

    def test_entrada_invalida_no_tumba_eval_05(self) -> None:
        c1, c2 = self._login("atacante"), self._login("inocente")
        try:
            payload = b"ESTO NO ES JSON !!!"
            c1.sendall(struct.pack("!I", len(payload)) + payload)
            self.assertEqual(self._esperar(c1, "error").get("tipo"), "error")
            enviar_mensaje_tcp(c2, {"tipo": "mensaje_canal", "canal": "#general", "texto": "Intacto"})
            self.assertEqual(self._esperar(c2, "difusion_canal").get("texto"), "Intacto")
        finally:
            c1.close(); c2.close()

    def test_heartbeat_udp_req_08(self) -> None:
        c1 = self._login("hb_user")
        u = self.servidor.registro.obtener_usuario("hb_user")
        assert u is not None
        u.ultima_actividad = time.time() - 10.0
        prev = u.ultima_actividad
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            enviar_mensaje_udp(udp, {"tipo": "heartbeat", "usuario": "hb_user"}, ("127.0.0.1", self.p_udp))
            time.sleep(0.1)
            self.assertGreater(u.ultima_actividad, prev)
        finally:
            udp.close(); c1.close()


if __name__ == "__main__":
    unittest.main()
