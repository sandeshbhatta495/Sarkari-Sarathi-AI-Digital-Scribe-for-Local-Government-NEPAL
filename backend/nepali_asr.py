"""Temporary stub. Matches the interface main.py expects."""

class _Stub:
    pipe = None

    def load_model(self):
        return False

    def transcribe_audio_file(self, path):
        return ""

def get_nepali_asr():
    return _Stub()
