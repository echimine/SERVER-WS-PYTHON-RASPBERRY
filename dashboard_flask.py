from flask import Flask, render_template, jsonify, Response
import sys
import os
import threading
import json
import queue
from datetime import datetime

# Add parent directory to path for potential shared imports (but with lower priority)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Context import Context
from WSClient import WSClient
from Message import MessageType

app = Flask(__name__)

# Get WebSocket server config
ctx = Context.dev()

# Stockage des données
routing_logs = []
connected_clients = []

# Queues pour SSE
sse_queues = []

def push_to_sse(event_type, data):
    """Push un événement à tous les clients SSE"""
    event = {"type": event_type, "data": data, "timestamp": datetime.now().isoformat()}
    for q in sse_queues:
        q.put(event)

def on_message(msg):
    """Callback pour tous les messages reçus"""

    # Log de routage (message envoyé entre clients)
    if msg.message_type == MessageType.ADMIN.ROUTING_LOG:
        routing_logs.append(msg.value)
        print(f"[ROUTING] {msg.value['emitter']} -> {msg.value['receiver']} ({msg.value['message_type']})")
        push_to_sse("routing", msg.value)

    # Nouveau client connecté
    elif msg.message_type == MessageType.ADMIN.CLIENT_CONNECTED:
        print(f"[+] Client connecté: {msg.value['username']}")
        push_to_sse("client_connected", msg.value)

    # Client déconnecté
    elif msg.message_type == MessageType.ADMIN.CLIENT_DISCONNECTED:
        print(f"[-] Client déconnecté: {msg.value['username']}")
        push_to_sse("client_disconnected", msg.value)

    # Liste complète des clients (reçue à la connexion)
    elif msg.message_type == MessageType.ADMIN.CLIENT_LIST_FULL:
        global connected_clients
        connected_clients = msg.value
        print(f"[CLIENTS] {len(msg.value)} clients connectés")
        push_to_sse("client_list", msg.value)

    else:
        print(f"[MSG] {msg.message_type}: {msg.emitter} -> {msg.receiver}")

def on_connect():
    print("[ADMIN] Connecté au serveur WS")

def on_users_list(users):
    pass  # Géré par CLIENT_LIST_FULL pour les admins

# Client WS en mode ADMIN
ws_client = WSClient(
    ctx=ctx,
    username="ADMIN_123",
    on_connect_callback=on_connect,
    on_message_callback=on_message,
    on_users_list_callback=on_users_list
)

@app.route('/')
def index():
    return render_template('index.html', ws_url=ctx.url())

@app.route('/api/config')
def get_config():
    return jsonify({
        'ws_url': ctx.url(),
        'host': ctx.host,
        'port': ctx.port
    })

@app.route('/api/clients')
def get_clients():
    return jsonify(connected_clients)

@app.route('/api/logs')
def get_logs():
    return jsonify(routing_logs[-100:])

@app.route('/api/stream')
def stream():
    """SSE endpoint pour recevoir les événements en temps réel"""
    print(f"[SSE] Nouvelle connexion client : {datetime.now()}")
    def event_stream():
        q = queue.Queue()
        sse_queues.append(q)
        # Envoyer un premier événement pour confirmer la connexion au client
        yield f"data: {json.dumps({'type': 'system', 'data': 'Connected to SSE'})}\n\n"
        try:
            while True:
                event = q.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            print(f"[SSE] Client déconnecté")
            sse_queues.remove(q)

    return Response(event_stream(), mimetype='text/event-stream')

def start_ws_client():
    ws_client.connect()

if __name__ == '__main__':
    # Lancer le client WS dans un thread
    ws_thread = threading.Thread(target=start_ws_client, daemon=True)
    ws_thread.start()

    print(f"Admin Dashboard running at http://127.0.0.1:5005")
    print(f"WebSocket server at {ctx.url()}")
    app.run(debug=False, port=5005, threaded=True)
 