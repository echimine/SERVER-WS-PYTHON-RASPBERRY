"""
rpi_client.py — Client Raspberry Pi avec micro INMP441 I2S et bouton arcade.

Câblage :
  INMP441  SCK  → GPIO 18 (Pin 12)
  INMP441  WS   → GPIO 19 (Pin 35)
  INMP441  SD   → GPIO 20 (Pin 38)
  INMP441  VDD  → 3.3V    (Pin 1)
  INMP441  GND  → GND     (Pin 6)
  INMP441  L/R  → GND     (Pin 6)   # force canal LEFT

  Bouton   T1   → GPIO 17 (Pin 11)
  Bouton   T2   → GND     (Pin 9)

Config OS requise (une fois) :
  Ajouter dans /boot/firmware/config.txt :
    dtoverlay=googlevoicehat-soundcard
  Puis rebooter et vérifier avec : arecord -l

Comportement :
  1er clic  → début de l'enregistrement
  2ème clic → arrêt + encodage WAV + envoi ENVOI_AUDIO à ANALYSEUR
"""

import base64
import io
import threading
import time

import numpy as np
import sounddevice as sd
from gpiozero import Button
from scipy.io.wavfile import write as wav_write

from Context import Context
from Message import Message, MessageType
from WSClient import WSClient

# ---------------------------------------------------------------------------
# Constantes — ajuster selon l'environnement
# ---------------------------------------------------------------------------
EMITTER      = "RPI_CLIENT"
RECEIVER     = "ANALYSEUR"
BUTTON_PIN   = 17       # BCM — Pin 11 physique
SAMPLE_RATE  = 16000    # Hz — 16kHz idéal pour la voix
DTYPE        = "int32"  # INMP441 : 24-bit dans frame 32-bit
MAX_DURATION = 60       # secondes max d'enregistrement (sécurité auto-stop)

# Mettre à None pour auto-détection, ou à un entier si plusieurs cartes ALSA.
# Afficher les périphériques disponibles avec : python3 -c "import sounddevice; print(sounddevice.query_devices())"
DEVICE_INDEX = None


# ---------------------------------------------------------------------------
# Machine à états
# ---------------------------------------------------------------------------
class State:
    IDLE      = "IDLE"
    RECORDING = "RECORDING"
    SENDING   = "SENDING"


state      = State.IDLE
state_lock = threading.Lock()

# Buffer d'enregistrement
_audio_chunks: list  = []
_stream: sd.InputStream | None = None
_auto_stop_timer: threading.Timer | None = None

# Référence globale au client WS
ws_client: WSClient | None = None


# ---------------------------------------------------------------------------
# Enregistrement
# ---------------------------------------------------------------------------
def _audio_callback(indata, frames, time_info, status):
    """Callback sounddevice — accumule le canal LEFT (index 0)."""
    _audio_chunks.append(indata[:, 0].copy())


def start_recording():
    global state, _audio_chunks, _stream, _auto_stop_timer

    _audio_chunks = []

    _stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=2,          # capture stéréo, on prend channel 0 (LEFT)
        dtype=DTYPE,
        device=DEVICE_INDEX,
        callback=_audio_callback,
    )
    _stream.start()

    # Sécurité : arrêt automatique après MAX_DURATION secondes
    _auto_stop_timer = threading.Timer(MAX_DURATION, _auto_stop)
    _auto_stop_timer.daemon = True
    _auto_stop_timer.start()

    state = State.RECORDING
    print(f"[{EMITTER}] Enregistrement démarré... (clic pour arrêter)")


def _auto_stop():
    """Arrêt automatique après MAX_DURATION secondes."""
    print(f"[{EMITTER}] Durée max atteinte ({MAX_DURATION}s) — arrêt automatique.")
    with state_lock:
        if state == State.RECORDING:
            threading.Thread(target=stop_and_send, daemon=True).start()


def stop_and_send():
    global state, _stream, _auto_stop_timer

    # Annuler le timer auto-stop si toujours actif
    if _auto_stop_timer is not None:
        _auto_stop_timer.cancel()
        _auto_stop_timer = None

    # Arrêter le stream
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None

    with state_lock:
        state = State.SENDING

    print(f"[{EMITTER}] Enregistrement terminé. Encodage en cours...")

    if not _audio_chunks:
        print(f"[{EMITTER}] Aucun audio capturé.")
        with state_lock:
            state = State.IDLE
        return

    # Concaténer les chunks (canal LEFT)
    audio_data = np.concatenate(_audio_chunks)

    # Encoder en WAV en mémoire
    buf = io.BytesIO()
    wav_write(buf, SAMPLE_RATE, audio_data)
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

    duration = len(audio_data) / SAMPLE_RATE
    print(f"[{EMITTER}] Audio : {duration:.1f}s — envoi vers {RECEIVER}...")

    # Envoyer
    if ws_client is not None:
        msg = Message(
            message_type=MessageType.ENVOI.AUDIO,
            emitter=EMITTER,
            receiver=RECEIVER,
            value=b64_str,
        )
        ws_client.send(msg)
        print(f"[{EMITTER}] Envoyé.")
    else:
        print(f"[{EMITTER}] Erreur : client WS non connecté.")

    with state_lock:
        state = State.IDLE

    print(f"[{EMITTER}] Prêt. Clic pour enregistrer.")


# ---------------------------------------------------------------------------
# Gestion du bouton
# ---------------------------------------------------------------------------
def on_button_pressed():
    global state

    with state_lock:
        current = state

    if current == State.IDLE:
        with state_lock:
            # Vérifier à nouveau sous le lock
            if state == State.IDLE:
                start_recording()

    elif current == State.RECORDING:
        with state_lock:
            if state == State.RECORDING:
                state = State.SENDING  # réserver l'état avant de lancer le thread
        threading.Thread(target=stop_and_send, daemon=True).start()

    # Si SENDING : ignorer le clic


# ---------------------------------------------------------------------------
# Callbacks WS
# ---------------------------------------------------------------------------
def on_connect():
    print(f"[{EMITTER}] Connecté au serveur. Prêt.")
    print(f"[{EMITTER}] Clic pour démarrer l'enregistrement.")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"[{EMITTER}] Démarrage...")
    print(f"[{EMITTER}] Périphériques audio disponibles :")
    print(sd.query_devices())
    print()

    # Connexion WebSocket
    ctx = Context.prod()  # remplacer par Context.dev() si en développement
    ws_client = WSClient(
        ctx=ctx,
        username=EMITTER,
        on_connect_callback=on_connect,
        on_message_callback=None,
        on_users_list_callback=None,
    )
    ws_client.connect_async()

    # Laisser le temps à la connexion de s'établir
    time.sleep(1)

    # Initialiser le bouton
    button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.05)
    button.when_pressed = on_button_pressed

    print(f"[{EMITTER}] Bouton GPIO{BUTTON_PIN} prêt.")

    # Boucle principale — maintenir le process vivant
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\n[{EMITTER}] Arrêt.")
        if _stream is not None:
            _stream.stop()
            _stream.close()
