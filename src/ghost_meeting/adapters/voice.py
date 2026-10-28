"""Voice side of the room dialogue: speaks the reservation question out loud."""

import subprocess
import tempfile
import threading
import wave
from collections.abc import Callable
from pathlib import Path

from piper import PiperVoice

from ghost_meeting.core.actions import AskToReserve

QUESTION = "Odayı sizin için ayıralım mı?"


class VoicePrompter:
    """Says the question through `speak`, whatever engine that wraps (Piper, ...)."""

    def __init__(self, speak: Callable[[str], None]) -> None:
        self._speak = speak

    def ask_to_reserve(self, action: AskToReserve) -> None:
        self._speak(QUESTION)


def piper_speaker(model_path: Path) -> Callable[[str], None]:
    """Load the Piper model once; the returned function says a text out loud.

    Not unit-tested: it needs the real model and a speaker, so it is checked by ear
    (scripts/speak_text.py, run_room.py --voice).
    """
    voice = PiperVoice.load(model_path)  # slow, so done once, not on every sentence

    def speak(text: str) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            with wave.open(tmp.name, "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
            # paplay plays through WSLg's PulseAudio; it blocks until the sound ends
            subprocess.run(["paplay", tmp.name], check=True)

    return speak


def speak_in_background(speak: Callable[[str], None]) -> Callable[[str], None]:
    """Wrap `speak` so it runs on its own thread and returns at once.

    Speaking takes seconds; without this the camera loop would freeze meanwhile.
    """

    def speak_async(text: str) -> None:
        threading.Thread(target=speak, args=(text,), daemon=True).start()

    return speak_async
