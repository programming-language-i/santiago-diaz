## 1. Consultar el precio de 30 productos en 30 APIs distintas.
"""
Hilos: el programa casi no calcula, solo espera respuestas de red, y con varios hilos esas 30 esperas ocurren a la vez en lugar de una tras otra.
"""