import os
import struct
import wave
import pyttsx3
import scipy.signal
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_FILE = os.path.join(SCRIPT_DIR, "recognised_items.txt")
AUDIO_DIR = os.path.join(SCRIPT_DIR, "audio")
TARGET_RATE = 44100


def convert_wav(src, dst):
    """Convert a WAV file to mono 16-bit 44100 Hz."""
    with wave.open(src, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    # Decode samples to float
    if sampwidth == 2:
        fmt = f"<{len(raw) // 2}h"
        samples = np.array(struct.unpack(fmt, raw), dtype=np.float64)
        samples /= 32768.0
    elif sampwidth == 1:
        samples = np.array(list(raw), dtype=np.float64)
        samples = (samples - 128) / 128.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    # Downmix to mono
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    # Resample to target rate
    if framerate != TARGET_RATE:
        num_samples = int(len(samples) * TARGET_RATE / framerate)
        samples = scipy.signal.resample(samples, num_samples)

    # Convert back to 16-bit PCM
    samples = np.clip(samples * 32768, -32768, 32767).astype(np.int16)

    with wave.open(dst, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(TARGET_RATE)
        wf.writeframes(samples.tobytes())


def main():
    os.makedirs(AUDIO_DIR, exist_ok=True)

    with open(ITEMS_FILE, "r") as f:
        items = [line.strip() for line in f if line.strip()]

    tmp_path = os.path.join(AUDIO_DIR, "_tmp.wav")
    generated = 0
    skipped = 0

    for i, item in enumerate(items):
        out_path = os.path.join(AUDIO_DIR, f"{item}.wav")
        if os.path.exists(out_path):
            skipped += 1
            continue

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.save_to_file(item, tmp_path)
            engine.runAndWait()
            engine.stop()
            del engine

            if os.path.exists(tmp_path):
                convert_wav(tmp_path, out_path)
                os.remove(tmp_path)
                generated += 1
                print(f"  [{i+1}/{len(items)}] + {item}")
            else:
                print(f"  [{i+1}/{len(items)}] ! {item} (no output)")
        except Exception as e:
            print(f"  [{i+1}/{len(items)}] ! {item} ({e})")

    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    print(f"\nDone: {generated} generated, {skipped} skipped (already exist)")


if __name__ == "__main__":
    main()
