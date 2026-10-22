"""Pruebas unitarias para estado, identidad y canales (Hitos 1-2)."""
import socket, sys, time, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.config import CANAL_GENERAL
from mensajeria.estado import EstadoDisponibilidad, RegistroConectados


class TestRegistroConectados(unittest.TestCase):

    def setUp(self) -> None:
        self.registro = RegistroConectados()
        self.sock1, self.sock1_peer = socket.socketpair()
        self.sock2, self.sock2_peer = socket.socketpair()

    def tearDown(self) -> None:
        for s in [self.sock1, self.sock1_peer, self.sock2, self.sock2_peer]:
            try: s.close()
            except OSError: pass

    def test_registro_exitoso_y_canal_general(self) -> None:
        ok, _, u = self.registro.registrar_usuario("carlos_recepcion", self.sock1, ("127.0.0.1", 10001))
        self.assertTrue(ok)
        self.assertIsNotNone(u)
        assert u is not None
        self.assertEqual(u.nombre, "carlos_recepcion")
        self.assertIn(CANAL_GENERAL, u.canales)
        self.assertEqual(u.estado, EstadoDisponibilidad.ACTIVO)

    def test_rechazo_duplicado_req_01(self) -> None:
        self.assertTrue(self.registro.registrar_usuario("sergio", self.sock1, ("127.0.0.1", 10001))[0])
        ok, msg, u = self.registro.registrar_usuario("sergio", self.sock2, ("127.0.0.1", 10002))
        self.assertFalse(ok)
        self.assertIsNone(u)
        self.assertIn("Ya existe", msg)
        self.assertFalse(self.registro.registrar_usuario("SERGIO", self.sock2, ("127.0.0.1", 10002))[0])

    def test_canales_por_area_req_11(self) -> None:
        self.registro.registrar_usuario("ana", self.sock1, ("127.0.0.1", 10001))
        ok, _ = self.registro.unir_a_canal("ana", "#recepcion")
        self.assertTrue(ok)
        u = self.registro.obtener_usuario("ana")
        assert u is not None
        self.assertIn("#recepcion", u.canales)
        self.assertTrue(self.registro.salir_de_canal("ana", "#recepcion")[0])
        self.assertNotIn("#recepcion", u.canales)
        self.assertFalse(self.registro.salir_de_canal("ana", CANAL_GENERAL)[0])
        self.assertIn(CANAL_GENERAL, u.canales)

    def test_disponibilidad_15s_req_08(self) -> None:
        self.registro.registrar_usuario("op1", self.sock1, ("127.0.0.1", 10001))
        u = self.registro.obtener_usuario("op1")
        assert u is not None
        u.ultima_actividad = time.time() - 20.0
        cambios = self.registro.verificar_disponibilidad(umbral_segundos=15.0)
        self.assertEqual(len(cambios), 1)
        self.assertEqual(cambios[0][1], EstadoDisponibilidad.INACTIVO)
        self.registro.actualizar_actividad("op1")
        self.assertEqual(u.estado, EstadoDisponibilidad.ACTIVO)


if __name__ == "__main__":
    unittest.main()
