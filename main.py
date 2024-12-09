import os
import socket
import json
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer
from multiprocessing import Process
from pathlib import Path
from pymongo import MongoClient
from urllib.parse import unquote_plus


STATIC_DIR = Path(__file__).parent / "static"
SOCKET_HOST = "0.0.0.0"
SOCKET_PORT = 5000
HTTP_PORT = 3000
MONGO_URI = "mongodb://mongo:27017/"
DB_NAME = "messages_db"
COLLECTION_NAME = "messages"


# Web application
class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"
        elif self.path not in ["/index.html", "/message.html", "/style.css", "/logo.png"]:
            self.path = "/error.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/message":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            data = dict(item.split("=") for item in post_data.split("&"))
            username = unquote_plus(data.get("username", "anonymous"))
            message = unquote_plus(data.get("message", ""))

            # Send data to Socket Server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((SOCKET_HOST, SOCKET_PORT))
                sock.sendall(json.dumps({"username": username, "message": message}).encode("utf-8"))

            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def run_http_server():
    os.chdir(STATIC_DIR)
    server = HTTPServer(("0.0.0.0", HTTP_PORT), CustomHandler)
    print(f"HTTP Server running on port {HTTP_PORT}...")
    server.serve_forever()


# Socket Server
def run_socket_server():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SOCKET_HOST, SOCKET_PORT))
    server_socket.listen(5)
    print(f"Socket Server running on port {SOCKET_PORT}...")

    while True:
        conn, _ = server_socket.accept()
        with conn:
            data = conn.recv(1024)
            if not data:
                continue
            message = json.loads(data.decode("utf-8"))
            message["date"] = datetime.now().isoformat()
            collection.insert_one(message)
            print(f"Message saved: {message}")


if __name__ == "__main__":
    # Start both servers in separate processes
    http_process = Process(target=run_http_server)
    socket_process = Process(target=run_socket_server)

    http_process.start()
    socket_process.start()

    http_process.join()
    socket_process.join()