"""Pruebas para reporte funcional (Hito 3)."""
import sys, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.reporte import (
    MetricasOperacion, es_mensaje_valido, extraer_emisor, extraer_hora,
    extraer_palabras_mensaje, generar_texto_reporte, procesar_bitacora_stream,
)


class TestReporte(unittest.TestCase):

    def test_funciones_puras_extraccion(self) -> None:
        msg = {"emisor": "carlos", "canal": "#recepcion",
               "texto": "Llegaron 30 cajas de repuestos urgentes", "timestamp": "2026-10-18T14:35:10Z"}
        self.assertEqual(extraer_emisor(msg), "carlos")
        self.assertEqual(extraer_hora(msg), 14)
        palabras = extraer_palabras_mensaje(msg)
        self.assertIn("llegaron", palabras)
        self.assertIn("cajas", palabras)
        self.assertNotIn("de", palabras)
        self.assertTrue(es_mensaje_valido(msg))

    def test_reduccion_streaming(self) -> None:
        msgs = [
            {"emisor": "juan", "canal": "#general", "texto": "iniciando turno cargamento", "timestamp": "2026-10-18T08:00:00Z"},
            {"emisor": "juan", "canal": "#general", "texto": "cargamento verificado", "timestamp": "2026-10-18T08:30:00Z"},
            {"emisor": "maria", "canal": "#recepcion", "texto": "cargamento en muelle", "timestamp": "2026-10-18T14:15:00Z"},
            {"emisor": "juan", "canal": "#general", "texto": "listo pedido despacho", "timestamp": "2026-10-18T14:45:00Z"},
        ]
        m = procesar_bitacora_stream(iter(msgs))
        self.assertEqual(m.total_mensajes, 4)
        self.assertEqual(m.conteo_emisores.most_common(1)[0], ("juan", 3))
        self.assertEqual(m.conteo_horas[8], 2)
        self.assertEqual(m.conteo_horas[14], 2)
        self.assertEqual(m.conteo_palabras["cargamento"], 3)

    def test_texto_reporte_secciones(self) -> None:
        msgs = [{"emisor": "op1", "canal": "#alistamiento", "texto": "caja pallet", "timestamp": "2026-10-18T10:00:00Z"}]
        texto = generar_texto_reporte(procesar_bitacora_stream(iter(msgs)))
        for seccion in ["REPORTE DE OPERACIÓN", "TOP EMISORES", "DISTRIBUCIÓN", "PALABRAS", "op1"]:
            self.assertIn(seccion, texto)


if __name__ == "__main__":
    unittest.main()
