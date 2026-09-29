## 4. Aplicar un filtro de desenfoque a 200 fotos, píxel por píxel, en Python puro.
"""
Procesos: es cálculo intensivo sin esperas, y como el GIL impide el paralelismo con hilos, se reparten las fotos entre núcleos con procesos
"""