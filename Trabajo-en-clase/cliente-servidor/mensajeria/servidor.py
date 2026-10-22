import socket
import threading

HOST = "127.0.0.1"
PORT = 8080

clientes = []
lock = threading.Lock()

def enviar_mensajes(mensaje, cliente_actual=None):
    print(f"Funcion de atencion de mensajes")
    with lock:
        for cliente in clientes:
            if cliente != cliente_actual:
                try:
                    cliente.sendall(mensaje)
                except OSError:
                    print("Error")
def atender_clientes(conexion, direccion):
    print(f"Cliente conectado: {direccion}")

    with lock:
        clientes.append(conexion)

    try:
        # NUEVO: el primer mensaje del cliente es su nombre
        nombre = conexion.recv(1024).decode()
        print(f"{nombre} se ha conectado desde {direccion}")

        while True:
            datos = conexion.recv(1024)

            if not datos:
                break
            # NUEVO: se muestra y se reenvía con el nombre
            print(f"[{nombre}]: {datos.decode()}")
            enviar_mensajes(f"{nombre}: {datos.decode()}".encode(), conexion)

    except ConnectionResetError:
        print(f"Cliente desconectado: {direccion}")
    finally:
        with lock:
            if conexion in clientes:
                clientes.remove(conexion)
        conexion.close()

        print(f"Cliente desconectado: {direccion}")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    servidor.bind((HOST, PORT))
    servidor.listen()

    print(f"Servidor escuchando en {HOST}:{PORT}")

    while True:
        conexion, direccion = servidor.accept()

        hilo = threading.Thread(target=atender_clientes, args=(conexion, direccion))
        
        hilo.start()