"""Try the Turkish Piper voice: python scripts/speak_text.py ["text to say"]

Writes the speech to a WAV file, then plays it through WSLg's PulseAudio.
"""

import subprocess
import sys
import wave
from pathlib import Path

from piper import PiperVoice

MODEL = Path("models/tts/tr_TR-dfki-medium.onnx")
OUTPUT = Path("/tmp/speak_text.wav")
DEFAULT_TEXT = "Odayı sizin için ayıralım mı?"


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEXT
    voice = PiperVoice.load(MODEL)  # reads the .onnx model and its .onnx.json settings
    with wave.open(str(OUTPUT), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    print(f"Saved {OUTPUT}, playing...")
    subprocess.run(["paplay", str(OUTPUT)], check=True)


if __name__ == "__main__":
    main()
