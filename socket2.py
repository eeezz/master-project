import json
import socket
import subprocess
import threading
import os
import time

BUFFER_SIZE = 4096
HOST = 'localhost' # If hosted on a ripper with the interface elsewhere, use tunnelforwarding instead of solely the socket connection.
PORT = 10022  # Choose any port number that is not already in use

def handle_client_connection(client_socket):
    try:
        data = client_socket.recv(BUFFER_SIZE).decode()
        received_data = json.loads(data)

        participant_id = received_data.get("participant_id")
        maze_strings = received_data.get("maze_data")
        print("Received participant ID:", participant_id)
        print("Received maze strings:", maze_strings)

        data_file = f"data_{participant_id}.json"
        with open(data_file, "w") as f:
            json.dump(received_data, f)

        # SLURM
        slurm_command = ["sbatch", "worker.slurm", data_file]
        subprocess.run(slurm_command)

        # Wait for SLURM job to complete (still simple way to wait, make into more robust solution if see is needed)
        output_file = f"image_paths_{participant_id}.json"
        while not os.path.exists(output_file):
            time.sleep(5)
        with open(output_file, 'r') as f:
            image_paths = json.load(f)

        # Send images back to client
        response_data = json.dumps(image_paths)
        client_socket.sendall(response_data.encode())

    except Exception as e:
        print("Error:", e)

    finally:
        client_socket.close()

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (HOST, PORT)
    server_socket.bind(server_address)
    server_socket.listen(5)
    print(f"Server listening on {HOST}:{PORT}")

    try:
        while True:  # Must accept client connection and state so
            client_socket, client_address = server_socket.accept()
            print("Accepted connection from", client_address)
            # Make a new thread
            client_thread = threading.Thread(target=handle_client_connection, args=(client_socket,))
            client_thread.start()

    except KeyboardInterrupt:
        print("Server stopped.")

    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
