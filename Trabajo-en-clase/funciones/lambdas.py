#doble = lambda x: x * 2

#print(doble(4))

## Dobles de lista

#numeros = [1, 2, 3, 4, 5, 6, 7, 8]

#dobles = map(lambda n: n * 2, numeros)

#dobles_list = list(dobles)

#print(f"Resultado: {dobles_list}")

####

estudiantes = ["Potazio", "Mogollon", "Jurado", "Castro", "Duque"]

apellidos_largos = filter(lambda apellido: len(apellido) > 6, estudiantes)


resultado = list(apellidos_largos)

print(f"Apellidos: {resultado}")