"""Generador de bitácora simulada (~100k mensajes, 1 mes de operación)."""
import argparse, json, random, sys, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensajeria.config import (ARCHIVO_BITACORA_POR_DEFECTO, CANAL_ALISTAMIENTO,
                                CANAL_DESPACHO, CANAL_GENERAL, CANAL_RECEPCION)

OPERARIOS = [
    "supervisor_t1", "juan_rec1", "maria_rec2", "pedro_rec3", "andres_ali1",
    "laura_ali2", "camila_ali3", "felipe_ali4", "carlos_des1", "diego_des2",
    "sofia_des3", "daniela_des4", "oscar_mon1",
    "supervisor_t2", "esteban_rec4", "natalia_rec5", "jorge_rec6", "paula_ali5",
    "mateo_ali6", "valentina_ali7", "sebastian_ali8", "julian_des5", "ricardo_des6",
    "tatiana_des7", "gabriel_des8", "monica_mon2",
    "supervisor_t3", "hugo_rec7", "fernando_rec8", "claudia_ali9", "mauricio_ali10",
    "lucia_ali11", "alvaro_des9", "alejandro_des10", "marcela_des11", "patricia_des12",
    "jefe_operaciones", "analista_inventario", "coordinador_seguridad", "calidad_auditor",
]

# Declarativo: diccionario canal -> frases
FRASES = {
    CANAL_RECEPCION: [
        "Llegó tractomula con 40 estibas de mercancía importada",
        "Falta remisión del proveedor en muelle 3",
        "Descargue finalizado en muelle 1, mercancía lista para conteo",
        "Incidencia detectada: caja averiada en lote 5410",
        "Camión con materia prima esperando autorización en portería",
        "Conteo físico completado sin novedades en recepción",
        "Estiba con sobrepeso, reubicando en zona de pesaje",
    ],
    CANAL_ALISTAMIENTO: [
        "Iniciando picking para pedido corporativo lote B",
        "Faltan 15 unidades de referencia A320 en estantería 12",
        "Pedido prioritario listo para embalaje y etiquetado",
        "Pallet consolidado en zona de búfer 2",
        "Se requiere recarga de montacargas eléctrico en pasillo 4",
        "Verificación de código de barras completada para pedido 8892",
        "Alistamiento de línea de farmacia al 90%",
    ],
    CANAL_DESPACHO: [
        "Camión de ruta norte cargado al 100%, sellando precinto",
        "Retraso de 20 minutos por verificación de factura en rampa 5",
        "Despacho completado con 120 bultos hacia la sucursal centro",
        "Faltó una guía de transporte para la ruta sur",
        "Vehículo despachado con éxito a las instalaciones del cliente",
        "Muelle 4 despejado y listo para la siguiente carga",
    ],
    CANAL_GENERAL: [
        "Reunión de cambio de turno en 10 minutos en sala operativa",
        "Recordatorio: uso obligatorio de botas y chaleco reflectivo",
        "Supervisor solicita reporte de novedades del turno",
        "Capacitación de seguridad industrial para nuevos operarios",
        "Aviso general: limpieza programada de pasillos a las 18:00",
    ],
}

CANALES = list(FRASES.keys())


def generar_bitacora_simulada(ruta: Path, cantidad: int = 100000, dias: int = 30) -> None:
    """Genera archivo JSONL con volumen realista."""
    print(f"Generando {cantidad:,} mensajes en '{ruta}'...")
    t0 = time.perf_counter()
    base = datetime.now(timezone.utc) - timedelta(days=dias)
    total_seg = dias * 86400

    if ruta.parent and not ruta.parent.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta, "w", encoding="utf-8") as f:
        for i in range(1, cantidad + 1):
            offset = max(0, min(int((i / cantidad) * total_seg) + random.randint(-60, 60), total_seg))
            ts = (base + timedelta(seconds=offset)).isoformat()
            emisor = random.choice(OPERARIOS)

            if random.random() < 0.15:  # 15% privados
                dest = random.choice([o for o in OPERARIOS if o != emisor])
                reg = {"tipo": "difusion_privada", "id": str(uuid.uuid4()), "emisor": emisor,
                       "destinatario": dest,
                       "texto": f"Revisemos la novedad del pedido de {random.choice(['repuestos', 'electrónica', 'ropa', 'alimentos'])}.",
                       "timestamp": ts}
            else:
                canal = random.choice(CANALES)
                reg = {"tipo": "difusion_canal", "id": str(uuid.uuid4()), "emisor": emisor,
                       "canal": canal, "texto": f"{random.choice(FRASES[canal])}. Código {random.randint(100, 999)}.",
                       "timestamp": ts}

            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
            if i % 25000 == 0:
                print(f"  {i:,} / {cantidad:,} escritos...")

    dt = time.perf_counter() - t0
    print(f"Completado en {dt:.2f}s. Tamaño: {ruta.stat().st_size / 1048576:.2f} MB.")


def main() -> None:
    p = argparse.ArgumentParser(description="Genera bitácora simulada.")
    p.add_argument("--cantidad", type=int, default=100000)
    p.add_argument("--dias", type=int, default=30)
    p.add_argument("--salida", default=ARCHIVO_BITACORA_POR_DEFECTO)
    args = p.parse_args()
    generar_bitacora_simulada(Path(args.salida), args.cantidad, args.dias)


if __name__ == "__main__":
    main()
