import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# List of packages to install
packages = [
    "SpeechRecognition",
    "ollama",
    "edge_tts",
    "sounddevice",
    "soundfile"
]

for package in packages:
    install(package)
