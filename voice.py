import threading
import json
import os
import sqlite3
import sounddevice as sd
import vosk


class VoiceToText:
    def __init__(self, model_path=None, db_path=None, device=None, use_grammar=True):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = model_path or os.path.join(base_dir, "vosk-model-small-en-us-0.15")
        self.db_path = db_path or os.path.join(base_dir, "data", "caddymate_store.db")
        self.device = device
        self.use_grammar = use_grammar

        self.model = None
        self.recognizer = None
        self.stream = None

        self.stop_event = threading.Event()

    # DATABASE
    def get_items_from_db(self):
        if not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM items")
        items = [row[0].strip().lower() for row in cur.fetchall()]
        conn.close()

        return sorted(set(filter(None, items)))

    def build_grammar(self, items):
        if not items:
            return None

        all_words = set(items)
        for item in items:
            for word in item.split():
                if word:
                    all_words.add(word.lower())

        return json.dumps(sorted(all_words))

    # MODEL
    def load_model(self):
        if self.model:
            return True

        if not os.path.exists(self.model_path):
            return False

        vosk.SetLogLevel(-1)
        self.model = vosk.Model(self.model_path)

        grammar = None
        if self.use_grammar:
            items = self.get_items_from_db()
            items = [item for item in items if item != "au"]
            grammar = self.build_grammar(items)

        self.recognizer = (
            vosk.KaldiRecognizer(self.model, 16000, grammar)
            if grammar else
            vosk.KaldiRecognizer(self.model, 16000)
        )

        self.recognizer.SetWords(True)
        return True

    # REAL-TIME RECORDING
    def start(self, on_result):
        if not self.load_model():
            return False

        self.stop_event.clear()

        def audio_callback(indata, frames, time_info, status):
            if self.stop_event.is_set():
                return

            data = bytes(indata)

            if self.recognizer.AcceptWaveform(data):
                res = json.loads(self.recognizer.Result())
                text = res.get("text", "")
                if text:
                    on_result(text, final=True)
            else:
                partial = json.loads(self.recognizer.PartialResult()).get("partial", "")
                if partial:
                    on_result(partial, final=False)

        self.stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=4000,
            dtype="int16",
            channels=1,
            device=self.device,
            callback=audio_callback
        )

        self.stream.start()
        return True

    def stop(self):
        self.stop_event.set()
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if self.recognizer:
            final = json.loads(self.recognizer.FinalResult()).get("text", "")
            if final:
                return final
        return ""
