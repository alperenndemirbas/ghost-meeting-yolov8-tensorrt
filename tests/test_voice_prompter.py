import threading

from ghost_meeting.adapters.voice import QUESTION, VoicePrompter, speak_in_background
from ghost_meeting.core.actions import AskToReserve
from ghost_meeting.core.ports import Prompter


def test_voice_prompter_speaks_the_reservation_question():
    spoken: list[str] = []
    prompter: Prompter = VoicePrompter(spoken.append)

    prompter.ask_to_reserve(AskToReserve("room1"))

    assert spoken == [QUESTION]


def test_speak_in_background_returns_before_the_speech_is_over():
    may_finish = threading.Event()
    finished = threading.Event()

    def slow_speak(text: str) -> None:
        may_finish.wait(timeout=5)  # pretends Piper is still talking
        finished.set()

    speak = speak_in_background(slow_speak)
    speak("merhaba")  # must come back while slow_speak is still blocked

    assert not finished.is_set()
    may_finish.set()
    assert finished.wait(timeout=5)
