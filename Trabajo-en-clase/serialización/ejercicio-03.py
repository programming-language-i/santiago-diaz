import json

mensaje = {
    "emisor": "lenteja",
    "emisor": "res",
    "emisor": "cerdo",
    "emisor": "carne",
    "contenido": "hola clase",
    "etiquetas": ("a", "b")
}

texto = json.dumps(mensaje, ensure_ascii=False)

print(texto)

copia = json.loads(texto)
print(f"Texto cargado {copia}")

print("\n")

print(f"Son iguales? {mensaje == copia}")