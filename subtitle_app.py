#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "textual",
#     "numpy",
#     "sounddevice",
#     "openai[realtime]",
# ]
#
# [tool.uv.sources]
# openai = { path = "../../", editable = true }
# ///
"""
Real-time subtitle application using OpenAI's Realtime API.
This app captures audio from the microphone (or mocks it), translates it to a target language,
and displays both the original speech and the translation instantly on the screen.

Usage:
    ./examples/realtime/subtitle_app.py [Target Language] [--mock]
    e.g., ./examples/realtime/subtitle_app.py Spanish
    e.g., ./examples/realtime/subtitle_app.py English --mock
"""

from __future__ import annotations

import base64
import asyncio
import argparse
from typing_extensions import override

import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None

from textual.app import App, ComposeResult
from textual.widgets import Static, RichLog
from textual.reactive import reactive
from textual.containers import Vertical, Container

from openai import AsyncOpenAI
from openai.resources.realtime.realtime import AsyncRealtimeConnection

# Audio configuration
SAMPLE_RATE = 24000
CHANNELS = 1


class StatusIndicator(Static):
    """A widget that shows the current status."""

    status = reactive("Connecting...")

    @override
    def render(self) -> str:
        return f"Status: {self.status}"


class ActiveSubtitle(Static):
    """A widget that shows the currently streaming subtitle."""

    original = reactive("")
    translated = reactive("")

    @override
    def render(self) -> str:
        orig = f"[dim]Original: {self.original}[/dim]" if self.original else ""
        trans = f"[bold #ff9e64]Translation: {self.translated}[/bold #ff9e64]" if self.translated else "..."
        if orig:
            return f"{orig}\n{trans}"
        return trans


class SubtitleApp(App[None]):
    CSS = """
    Screen {
        background: #1a1b26;
    }
    Container {
        border: double rgb(91, 164, 91);
        padding: 1 2;
    }
    #history {
        height: 1fr;
        border: round #3b4261;
        background: #24283b;
        color: #a9b1d6;
        margin-bottom: 1;
    }
    #active-container {
        height: 6;
        border: solid white;
        background: #1f2335;
        content-align: center middle;
    }
    #active-subtitle {
        text-align: center;
    }
    #status {
        height: 3;
        content-align: center middle;
        background: #2a2b36;
        margin-bottom: 1;
        color: #7aa2f7;
    }
    """

    def __init__(self, target_language: str = "English", mock: bool = False) -> None:
        super().__init__()
        self.client = AsyncOpenAI()
        self.connection: AsyncRealtimeConnection | None = None
        self.target_language = target_language
        self.mock = mock
        self._active_trans = ""
        self._active_orig = ""

    @override
    def compose(self) -> ComposeResult:
        with Container():
            yield StatusIndicator(id="status")
            yield RichLog(id="history", wrap=True, highlight=True, markup=True)
            with Vertical(id="active-container"):
                yield ActiveSubtitle(id="active-subtitle")

    async def on_mount(self) -> None:
        self.run_worker(self.main_loop())

    async def main_loop(self) -> None:
        status = self.query_one(StatusIndicator)
        history = self.query_one("#history", RichLog)
        active = self.query_one("#active-subtitle", ActiveSubtitle)

        try:
            async with self.client.realtime.connect(model="gpt-realtime") as conn:
                self.connection = conn
                status.status = f"Connected (Translating to {self.target_language})" + (
                    " [MOCK MODE]" if self.mock else ""
                )

                await conn.session.update(
                    session={
                        "instructions": (
                            f"You are a real-time translator. Translate all input speech to {self.target_language}. "
                            "Output ONLY the translated text. Do not add any conversational filler or greetings."
                        ),
                        "output_modalities": ["text"],
                        "audio": {
                            "input": {
                                "turn_detection": {"type": "server_vad"},
                                "transcription": {"model": "whisper-1"},
                            },
                        },
                        "model": "gpt-realtime",
                        "type": "realtime",
                    }
                )

                self.run_worker(self.send_mic_audio())

                async for event in conn:
                    # Original speech streaming
                    if event.type == "conversation.item.input_audio_transcription.delta":
                        self._active_orig += event.delta or ""
                        active.original = self._active_orig

                    elif event.type == "conversation.item.input_audio_transcription.completed":
                        self._active_orig = event.transcript
                        active.original = self._active_orig

                    # Translation streaming
                    elif event.type == "response.output_text.delta":
                        self._active_trans += event.delta
                        active.translated = self._active_trans

                    elif event.type == "response.output_text.done":
                        if self._active_trans.strip():
                            history.write(f"[dim]Input:[/dim] {self._active_orig.strip()}")
                            history.write(f"[bold cyan]Trans:[/bold cyan] {self._active_trans.strip()}")
                            history.write("-" * 20)

                        # Reset for next turn
                        self._active_trans = ""
                        self._active_orig = ""
                        active.translated = ""
                        active.original = ""

                    elif event.type == "error":
                        history.write(f"[red]API Error: {event.error}[/red]")

        except Exception as e:
            status.status = f"Error: {e}"
            history.write(f"[bold red]Exception:[/bold red] {e}")

    async def send_mic_audio(self) -> None:
        """Background worker to stream audio to the API."""
        read_size = int(SAMPLE_RATE * 0.02)

        if self.mock:
            await self._run_mock_audio(read_size)
            return

        if sd is None:
            return

        try:
            stream = sd.InputStream(
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                dtype="int16",
            )
            stream.start()

            while self.connection:
                if stream.read_available < read_size:
                    await asyncio.sleep(0.01)
                    continue

                data, _ = stream.read(read_size)
                await self.connection.input_audio_buffer.append(audio=base64.b64encode(data.tobytes()).decode("utf-8"))
        except Exception:
            pass
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    async def _run_mock_audio(self, read_size: int) -> None:
        """Simulate audio input for testing."""
        data = np.zeros(read_size, dtype=np.int16).tobytes()
        encoded = base64.b64encode(data).decode("utf-8")
        while self.connection:
            await self.connection.input_audio_buffer.append(audio=encoded)
            await asyncio.sleep(0.02)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("language", nargs="?", default="English")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    app = SubtitleApp(target_language=args.language, mock=args.mock)
    app.run()
