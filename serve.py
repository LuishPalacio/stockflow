"""Sobe o StockFlow para a rede local (qualquer computador da rede consegue
acessar pelo IP desta máquina).

Uso:
    python serve.py
"""
import socket

from waitress import serve

from app import app

PORT = 8000


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    ip = ip_local()
    print("StockFlow no ar.")
    print(f"  Neste computador: http://localhost:{PORT}")
    print(f"  Na rede local:    http://{ip}:{PORT}")
    print("Deixe esta janela aberta enquanto o sistema estiver em uso.")
    serve(app, host="0.0.0.0", port=PORT)
