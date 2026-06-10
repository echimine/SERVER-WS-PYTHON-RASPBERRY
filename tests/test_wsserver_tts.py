import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

try:
    import websocket_server  # noqa: F401
except ModuleNotFoundError:
    websocket_server = types.ModuleType("websocket_server")
    websocket_server.WebsocketServer = MagicMock
    sys.modules["websocket_server"] = websocket_server

from Context import Context
from Message import Message, MessageType
from WSServer import WSServer


class FakeVoice:
    def __init__(self):
        self.texts = []

    def synthesize_wav(self, text, wav_file):
        self.texts.append(text)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\0\0")


class WSServerTextToSpeechTests(unittest.TestCase):
    def setUp(self):
        websocket_server_patcher = patch("WSServer.WebsocketServer")
        self.addCleanup(websocket_server_patcher.stop)
        websocket_server = websocket_server_patcher.start()
        self.transport = websocket_server.return_value
        self.server = WSServer(Context("127.0.0.1", 8765))
        self.client = {"id": 1}

    def send(self, message):
        self.server.on_message_received(self.client, self.transport, message.to_json())

    def test_queues_text_from_analyseur_for_each_destination(self):
        for receiver in ("SERVER", "ALL", "DESTINATAIRE"):
            with self.subTest(receiver=receiver):
                self.server.enqueue_speech = MagicMock()
                self.send(Message(MessageType.ENVOI.TEXT, "ANALYSEUR", receiver, "Analyse terminee"))
                self.server.enqueue_speech.assert_called_once_with("Analyse terminee")

    def test_does_not_queue_text_from_another_emitter(self):
        self.server.enqueue_speech = MagicMock()

        self.send(Message(MessageType.ENVOI.TEXT, "CLIENT", "SERVER", "Bonjour"))

        self.server.enqueue_speech.assert_not_called()

    def test_does_not_queue_non_text_message_from_analyseur(self):
        self.server.enqueue_speech = MagicMock()

        self.send(Message(MessageType.ENVOI.IMAGE, "ANALYSEUR", "SERVER", "IMG:data"))

        self.server.enqueue_speech.assert_not_called()

    def test_speak_text_invokes_reused_voice_and_player(self):
        voice = FakeVoice()
        self.server.tts_voice = voice

        with patch.dict(os.environ, {"PIPER_PLAYER": "audio-player --quiet"}):
            with patch("WSServer.subprocess.run") as run:
                self.server.speak_text("Premier texte")
                self.server.speak_text("Second texte")

        self.assertEqual(voice.texts, ["Premier texte", "Second texte"])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args.args[0][:2], ["audio-player", "--quiet"])

    def test_get_tts_voice_loads_the_model_only_once(self):
        piper = types.ModuleType("piper")
        piper.PiperVoice = MagicMock()
        voice = FakeVoice()
        piper.PiperVoice.load.return_value = voice

        with patch.dict(sys.modules, {"piper": piper}):
            with patch.dict(os.environ, {"PIPER_MODEL": "/voices/fr.onnx"}):
                self.assertIs(self.server.get_tts_voice(), voice)
                self.assertIs(self.server.get_tts_voice(), voice)

        piper.PiperVoice.load.assert_called_once_with("/voices/fr.onnx")

    def test_tts_error_does_not_stop_forwarding_or_worker(self):
        receiver = {"id": 2}
        self.server.clients["CLIENT"] = receiver
        self.send(Message(MessageType.ENVOI.TEXT, "ANALYSEUR", "CLIENT", "A lire"))
        self.transport.send_message.assert_called_with(receiver, unittest.mock.ANY)
        self.assertEqual(self.server.tts_queue.get_nowait(), "A lire")
        self.server.tts_queue.task_done()

        self.server.tts_queue.put("Echec audio")
        self.server.running = True

        def fail_and_stop(_text):
            self.server.running = False
            raise RuntimeError("sortie audio absente")

        with patch.object(self.server, "speak_text", side_effect=fail_and_stop):
            self.server.tts_loop()

        self.assertEqual(self.server.tts_queue.unfinished_tasks, 0)

    def test_get_tts_voice_requires_a_model(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "PIPER_MODEL"):
                self.server.get_tts_voice()


if __name__ == "__main__":
    unittest.main()
