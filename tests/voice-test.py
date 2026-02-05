import sys
import os
import json
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from voice import VoiceToText

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
SAMPLE_RATE = 44100
CHUNK_SIZE = 4000


def build_grammar(vtt):
    if not vtt.use_grammar:
        return None
    items = vtt.get_items_from_db()
    items = [item for item in items if item != "au"]
    return vtt.build_grammar(items)


def recognize_file(vtt, filepath, grammar):
    import vosk

    wf = wave.open(filepath, "rb")

    if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
        wf.close()
        return None, "unsupported format (need mono 16-bit WAV)"

    file_rate = wf.getframerate()
    if file_rate != SAMPLE_RATE:
        wf.close()
        return None, f"sample rate mismatch (file={file_rate}, expected={SAMPLE_RATE})"

    recognizer = (
        vosk.KaldiRecognizer(vtt.model, SAMPLE_RATE, grammar)
        if grammar else
        vosk.KaldiRecognizer(vtt.model, SAMPLE_RATE)
    )
    recognizer.SetWords(True)

    while True:
        data = wf.readframes(CHUNK_SIZE)
        if len(data) == 0:
            break
        recognizer.AcceptWaveform(data)

    result = json.loads(recognizer.FinalResult())
    wf.close()
    return result.get("text", ""), None


def main():
    if len(sys.argv) > 1:
        # Single file mode: recognise one WAV and print the result
        filepath = sys.argv[1]
        if not os.path.isfile(filepath):
            print(f"File not found: {filepath}")
            sys.exit(1)
    else:
        filepath = None

    vtt = VoiceToText(use_grammar=True)
    if not vtt.load_model():
        print(f"Could not load model from {vtt.model_path}")
        sys.exit(1)

    grammar = build_grammar(vtt)

    if filepath:
        heard, error = recognize_file(vtt, filepath, grammar)
        if error:
            print(f"Error: {error}")
            sys.exit(1)
        print(heard if heard else "(silence)")
        return

    # Batch mode: run through all WAVs in the audio directory
    if not os.path.isdir(AUDIO_DIR):
        print(f"Audio directory not found: {AUDIO_DIR}")
        print("Create a 'tests/audio/' folder with WAV files, or pass a file path as an argument.")
        sys.exit(1)

    audio_files = [f for f in sorted(os.listdir(AUDIO_DIR)) if f.lower().endswith(".wav")]
    if not audio_files:
        print(f"No .wav files found in {AUDIO_DIR}")
        sys.exit(1)

    passed = []
    failed = []

    total = len(audio_files)
    for i, filename in enumerate(audio_files, 1):
        expected = os.path.splitext(filename)[0].lower()
        path = os.path.join(AUDIO_DIR, filename)

        print(f"[{i}/{total}] {expected} ... ", end="", flush=True)
        heard, error = recognize_file(vtt, path, grammar)

        if error:
            print(f"ERROR: {error}")
            failed.append((expected, f"[error] {error}"))
            continue

        if heard == expected:
            print("OK")
            passed.append(expected)
        else:
            print(f"FAIL (heard: {heard if heard else '(silence)'})")
            failed.append((expected, heard if heard else "(silence)"))

    pass_pct = len(passed) / total * 100 if total else 0
    fail_pct = len(failed) / total * 100 if total else 0

    lines = []
    lines.append(f"RESULTS: {len(passed)} passed, {len(failed)} failed out of {total} files")

    if passed:
        lines.append(f"\nCorrectly identified ({len(passed)}):")
        for item in passed:
            lines.append(f"  + {item}")

    if failed:
        lines.append(f"\nFailed to identify ({len(failed)}):")
        for expected, heard in failed:
            lines.append(f"  - {expected}  (heard: {heard})")

    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"  Total:  {total}")
    lines.append(f"  Passed: {len(passed)} ({pass_pct:.1f}%)")
    lines.append(f"  Failed: {len(failed)} ({fail_pct:.1f}%)")
    lines.append("")

    output = "\n".join(lines)
    print(output)

    results_path = os.path.join(os.path.dirname(__file__), "voice-test-results.txt")
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"Results saved to {results_path}")

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
