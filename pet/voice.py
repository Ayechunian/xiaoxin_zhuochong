import os
import shutil
import subprocess
from pathlib import Path


class VoiceEngine:
    """Non-blocking Windows SAPI voice with a playful childlike preset."""

    def __init__(self, script_path=None):
        self.script_path = Path(script_path or Path(__file__).with_name("speak.ps1"))
        self.process = None
        self.rate = 2
        self.pitch = 5
        self.volume = 90
        disabled = os.environ.get("DESKTOP_PET_DISABLE_AUDIO", "").lower() in ("1", "true", "yes")
        self.available = (os.name == "nt" and not disabled and self.script_path.exists()
                          and shutil.which("powershell.exe") is not None)

    def speak(self, text):
        if not self.available or not text.strip():
            return False
        self.stop()
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.process = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-File", str(self.script_path),
                 "-Text", text, "-Rate", str(self.rate),
                 "-Pitch", str(self.pitch), "-Volume", str(self.volume)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, creationflags=flags,
            )
            return True
        except OSError:
            self.available = False
            self.process = None
            return False

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
        self.process = None

    def close(self):
        self.stop()
