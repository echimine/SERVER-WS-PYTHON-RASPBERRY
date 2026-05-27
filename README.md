# SERVER-WS-PYTHON-RASPBERRY

Serveur WebSocket Python pour Raspberry Pi avec dashboard admin Flask.

## Architecture

```
WSServer.py          — Serveur WebSocket principal (port 8765 en dev)
dashboard_flask.py   — Dashboard admin web (port 5005)
Context.py           — Configuration host/port (dev / prod)
Message.py           — Protocole de messages
WSClient.py          — Client WebSocket (utilisé par le dashboard)
standard.json        — Spécification du protocole
```

## Installation

### 1. Cloner le repo

```bash
git clone git@github-echimine:echimine/SERVER-WS-PYTHON-RASPBERRY.git
cd SERVER-WS-PYTHON-RASPBERRY
```

### 2. Créer l'environnement virtuel

```bash
python3 -m venv .venv
```

### 3. Installer les dépendances

```bash
.venv/bin/pip install -r requirements.txt
```

## Lancer le serveur WebSocket

```bash
.venv/bin/python WSServer.py
```

Le serveur écoute sur `ws://0.0.0.0:8765` (mode dev).

### Commandes CLI du serveur

Une fois démarré, le serveur propose une interface en ligne de commande :

| Commande | Description |
|---|---|
| `dest:message` | Envoyer un message texte à un client |
| `ALL:message` | Broadcaster à tous les clients |
| `img:dest:/chemin/image.png` | Envoyer une image |
| `audio:dest:/chemin/audio.mp3` | Envoyer un fichier audio |
| `video:dest:/chemin/video.mp4` | Envoyer une vidéo |
| `list` | Afficher les clients connectés |
| `disconnect` | Arrêter le serveur |

## Lancer le dashboard admin

Le serveur WebSocket doit être démarré avant le dashboard.

```bash
.venv/bin/python dashboard_flask.py
```

Dashboard disponible sur `http://127.0.0.1:5005`.

### Endpoints API

| Endpoint | Description |
|---|---|
| `GET /api/clients` | Liste des clients connectés |
| `GET /api/logs` | 100 derniers logs de routage |
| `GET /api/stream` | Flux SSE temps réel |
| `GET /api/config` | Configuration du serveur WS |

## Protocole de messages

Format JSON échangé sur le WebSocket :

```json
{
  "message_type": "ENVOI_TEXT",
  "data": {
    "emitter": "Client1",
    "receiver": "Client2",
    "value": "Bonjour",
    "sensor_id": null
  }
}
```

### Types de messages

| Type | Description |
|---|---|
| `DECLARATION` | Enregistrement d'un client au démarrage |
| `ENVOI_TEXT / IMAGE / AUDIO / VIDEO` | Envoi de contenu |
| `ENVOI_SENSOR` | Données capteur IoT |
| `RECEPTION_*` | Équivalents reçus côté client |
| `SYS_MESSAGE` | Accusé de réception (VU) |
| `ADMIN_*` | Événements réservés aux clients admin |

Un client admin se déclare avec un username `ADMIN` ou préfixé `ADMIN_`.

## Environnements

Modifier `Context.py` pour changer les paramètres :

| Env | Host | Port |
|---|---|---|
| dev | `0.0.0.0` | `8765` |
| prod | `172.28.55.77` | `9000` |

Pour utiliser le mode prod, remplacer `.dev()` par `.prod()` dans `WSServer.py` et `dashboard_flask.py`.
