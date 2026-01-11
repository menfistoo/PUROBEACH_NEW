"""
Real-time voice transcription for Claude Code
Supports mixed English/Portuguese/Spanish with accent handling

Usage:
    python scripts/voice_transcribe.py

Controls:
    - Press ENTER to start recording
    - Press ENTER again to stop and transcribe
    - Text is automatically copied to clipboard
    - Type 'q' + ENTER to quit

Just paste (Ctrl+V) into Claude Code after transcription!
"""

import sys
import threading
import numpy as np
import time

# Check dependencies before importing
def check_dependencies():
    missing = []
    try:
        import sounddevice
    except ImportError:
        missing.append("sounddevice")
    try:
        import faster_whisper
    except ImportError:
        missing.append("faster-whisper")
    try:
        import pyperclip
    except ImportError:
        missing.append("pyperclip")

    if missing:
        print("Missing dependencies. Install with:")
        print(f"    pip install {' '.join(missing)}")
        sys.exit(1)

check_dependencies()

import sounddevice as sd
import pyperclip
from faster_whisper import WhisperModel

# =============================================================================
# CONFIGURATION
# =============================================================================

# Model options: tiny, base, small, medium, large-v3
# Larger = better accent handling but slower
MODEL_SIZE = "small"  # Good balance for accents

# Device: "cpu" or "cuda" (if you have NVIDIA GPU)
DEVICE = "cpu"

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1

# =============================================================================
# TRANSCRIPTION ENGINE
# =============================================================================

class VoiceTranscriber:
    def __init__(self):
        print(f"Loading Whisper model '{MODEL_SIZE}'... (first time may download)")
        self.model = WhisperModel(
            MODEL_SIZE,
            device=DEVICE,
            compute_type="int8" if DEVICE == "cpu" else "float16"
        )
        print("Model loaded!\n")

        self.recording = False
        self.audio_data = []
        self.stream = None

    def start_recording(self):
        """Start recording from microphone"""
        self.audio_data = []
        self.recording = True

        def callback(indata, frames, time_info, status):
            if self.recording:
                self.audio_data.append(indata.copy())

        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=np.float32,
                callback=callback
            )
            self.stream.start()
            return True
        except Exception as e:
            print(f"Microphone error: {e}")
            self.recording = False
            return False

    def stop_recording(self):
        """Stop recording and return audio data"""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_data:
            return None

        return np.concatenate(self.audio_data, axis=0).flatten()

    def transcribe(self, audio):
        """Transcribe audio using Whisper"""
        if audio is None or len(audio) < SAMPLE_RATE * 0.5:
            return None

        segments, info = self.model.transcribe(
            audio,
            language=None,  # Auto-detect
            beam_size=5,  # Better for accents
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200
            )
        )

        text = " ".join([segment.text.strip() for segment in segments])
        lang = info.language if info.language_probability > 0.5 else "mixed"

        return text, lang

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 55)
    print("  VOICE TRANSCRIPTION FOR CLAUDE CODE")
    print("  English / Portuguese / Spanish + accent support")
    print("=" * 55)
    print()
    print("  [ENTER]      Start/stop recording")
    print("  [q + ENTER]  Quit")
    print()
    print("  Text is auto-copied to clipboard after transcription")
    print("=" * 55)

    transcriber = VoiceTranscriber()

    while True:
        try:
            cmd = input("\n>> Press ENTER to record: ").strip().lower()

            if cmd == 'q':
                print("Goodbye!")
                break

            # Start recording
            if not transcriber.start_recording():
                continue

            print("\n   RECORDING... (press ENTER to stop)")
            input()

            # Stop and process
            print("   Processing...")
            audio = transcriber.stop_recording()
            result = transcriber.transcribe(audio)

            if result is None:
                print("   No speech detected. Try again.")
                continue

            text, lang = result

            if not text.strip():
                print("   Could not transcribe. Try speaking louder.")
                continue

            # Copy to clipboard
            pyperclip.copy(text)

            print(f"\n   Language: {lang}")
            print("   " + "-" * 50)
            print(f"   {text}")
            print("   " + "-" * 50)
            print("\n   Copied! Paste with Ctrl+V")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n   Error: {e}")

if __name__ == "__main__":
    main()
