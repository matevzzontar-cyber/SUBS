# SUBS: Real-time Subtitle Application

A high-performance, low-latency application that captures microphone audio, translates it in real-time using OpenAI's Realtime API, and displays subtitles instantly in your terminal.

## Features

- **Dual Mode**: Displays both the **original speech** (via `whisper-1`) and the **translated text** simultaneously.
- **Real-time Streaming**: Incremental subtitle updates as you speak.
- **Hands-Free (Server VAD)**: Automatically detects speech start and end.
- **Instant Translation**: Configure any target language (Spanish, French, Japanese, etc.).
- **Terminal UI**: Modern interface with streaming active subtitles and a scrollable history log.
- **Mock Mode**: Test without a microphone using `--mock`.

## Prerequisites

- **Python**: 3.9 or higher (if running from source).
- **OpenAI API Key**: Set via `OPENAI_API_KEY` environment variable.
- **System Dependencies**:
  - **macOS**: `brew install portaudio`
  - **Ubuntu/Debian**: `sudo apt-get install libportaudio2`

## Installation & Usage (Python)

```bash
# Install dependencies
pip install "openai[subtitles]"

# Run the app (default to English)
python subtitle_app.py

# Run in mock mode (no mic needed)
python subtitle_app.py --mock

# Translate to a specific language
python subtitle_app.py Spanish
```

## Creating a Self-Contained Executable

You can package the app into a single executable file for your platform (Windows `.exe`, macOS/Linux binary) using the provided build script.

1. Install build dependencies:
   ```bash
   pip install pyinstaller "openai[subtitles]"
   ```

2. Run the build script from the repository root:
   ```bash
   python scripts/build_app.py
   ```

3. Find the executable in the `dist/` directory:
   - **Linux/macOS**: `./dist/subs`
   - **Windows**: `dist\subs.exe`

## How it Works

The app establishes a persistent WebSocket connection to OpenAI's Realtime API. It captures audio in 20ms chunks and streams them to the server. The server's Voice Activity Detection (VAD) identifies when you speak, and the model translates the audio into text, which is then streamed back to the terminal UI.
