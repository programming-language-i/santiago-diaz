import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("127.0.0.1", 8080))
    servidor.listen()

    print("Servidor escuchando en", servidor.getsockname())

    while True:
        conexion, direccion = servidor.accept()

        with conexion:
            print("Conexión establecida con:", direccion)

            datos = conexion.recv(1024).decode("utf-8")

            print("Cliente:", datos)

            conexion.sendall(datos.upper().encode("utf-8"))
