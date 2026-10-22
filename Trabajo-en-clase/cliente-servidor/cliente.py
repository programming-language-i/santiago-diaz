import socket
import os

nombre_cliente = os.path.basename(__file__)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
    cliente.connect(("127.0.0.1", 8080))

    print("Dirección del cliente:", cliente.getsockname())
    print("Dirección del servidor:", cliente.getpeername())

    # Enviar el nombre del archivo al servidor
    cliente.sendall(nombre_cliente.encode("utf-8"))

    # Recibir respuesta
    print(
        "respuesta del servidor:",
        cliente.recv(1024).decode("utf-8")
    )