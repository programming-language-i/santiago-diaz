import socket
import threading

HOST = "127.0.0.1"
PORT = 8080

def recibir_mensaje(conexion):
    while True:
        try:
            datos = conexion.recv(1024)

            if not datos:
                print("\nSe perdio conexion")
                break
            print(f"\nMensaje: {datos.decode()}")
            print(">", end=" ", flush=True)

        except ConnectionResetError:
            print("conexion terminada")
            break

# NUEVO: pedir el nombre antes de conectar
nombre = input("Tu nombre: ")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as   cliente:
    cliente.connect((HOST, PORT))

    # NUEVO: enviar el nombre como primer mensaje
    cliente.sendall(nombre.encode())

    print("conectado al servidor")
    print("Escribe, mensaje. Usa 'salir' para terminar la conexion")

    hilo = threading.Thread(target=recibir_mensaje, args=(cliente,), daemon=True)

    hilo.start()

    while True:
        mensaje = input(">")

        if mensaje.lower() == "salir":
            break
        
        cliente.sendall(mensaje.encode())