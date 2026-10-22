# Imperativo y declarativo

print ("Programación Imperativo y declarativo")

numeros = [1, 2, 3, 4, 5, 6, 7, 8]

#total = 0

# for n in numeros:
 #   if n % 2 == 0:
 #       total += n * n 
#print(f"Resultado: {total}") consume un recurso más, ya que se necesita una variable para almacenar el resultado y un bucle para iterar sobre la lista.

# Declarativo
#total = sum(n*n for n in numeros if n % 2 == 0)

#print(f"Resultado: {total}")


## -------------- funciones puras y de orden superior ---------

def es_par(n):
    return n % 2 == 0

def cuadrado(n):
    return n * n

total = sum(cuadrado(n) for n in numeros if es_par(n))
print(f"Resultado: {total}")


# uso filter
pares = filter(es_par, numeros)
pares_list = list(pares)

print(f"Resultado: {pares_list}")
