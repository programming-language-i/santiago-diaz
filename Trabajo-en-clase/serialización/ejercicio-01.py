import pickle

mensaje = {
  "emisor": "lenteja",
    "emisor": "res",
    "emisor": "cerdo",
    "emisor": "carne",
    "contenido": "hola clase",
    "etiquetas": ("a", "b")
}

datos = pickle.dumps(mensaje)

print(datos)
print("\n")

copia = pickle.loads(datos)
print(copia)