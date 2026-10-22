"""Pruebas unitarias para la bitácora auditable (Req 07)."""
import json, sys, tempfile, threading, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.bitacora import BitacoraAuditable


class TestBitacoraAuditable(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self.tmp.name) / "test.jsonl"
        self.bitacora = BitacoraAuditable(self.ruta)

    def tearDown(self) -> None:
        try:
            self.tmp.cleanup()
        except Exception:
            pass

    def test_registro_simple_y_formato_jsonl(self) -> None:
        msg = {"tipo": "difusion_canal", "emisor": "sergio", "canal": "#general",
               "texto": "Hola equipo", "timestamp": "2026-10-18T10:00:00Z"}
        self.bitacora.registrar_mensaje(msg)
        self.assertTrue(self.ruta.exists())
        lineas = self.ruta.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lineas), 1)
        self.assertEqual(json.loads(lineas[0]), msg)

    def test_concurrencia_multihilo_sin_perdida(self) -> None:
        n_hilos, msgs_por_hilo = 8, 50
        total = n_hilos * msgs_por_hilo

        def worker(hid: int) -> None:
            for j in range(msgs_por_hilo):
                self.bitacora.registrar_mensaje({"id_hilo": hid, "indice": j, "texto": f"H{hid}-{j}"})

        hilos = [threading.Thread(target=worker, args=(h,)) for h in range(n_hilos)]
        for h in hilos: h.start()
        for h in hilos: h.join()

        self.assertEqual(len(list(self.bitacora.iterar_mensajes())), total)
        self.assertEqual(self.bitacora.contar_mensajes(), total)

    def test_descarta_lineas_corruptas(self) -> None:
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(json.dumps({"id": 1, "texto": "valido"}) + "\n")
            f.write("CORRUPTA {NO JSON\n")
            f.write(json.dumps({"id": 2, "texto": "segundo"}) + "\n")
        msgs = list(self.bitacora.iterar_mensajes())
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["id"], 1)
        self.assertEqual(msgs[1]["id"], 2)


if __name__ == "__main__":
    unittest.main()
