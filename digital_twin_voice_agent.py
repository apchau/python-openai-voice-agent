import asyncio
import os
import smtplib
from email.mime.text import MIMEText

import openai
from agents import Agent
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    SingleAgentWorkflowCallbacks,
    VoicePipeline,
)

try:
    from examples.voice.static.util import record_audio, AudioPlayer
except ImportError:
    # fallback if examples module not available
    import sounddevice as sd
    import numpy as np
    import curses
    import time

    def _record_audio(screen: "curses.window") -> np.ndarray:
        screen.nodelay(True)
        screen.addstr("Press <space> to start/stop recording\n")
        screen.refresh()
        recording = False
        audio_buffer = []

        def _cb(indata, frames, time_info, status):
            if recording:
                audio_buffer.append(indata.copy())

        with sd.InputStream(samplerate=24000, channels=1, dtype=np.float32, callback=_cb):
            while True:
                key = screen.getch()
                if key == ord(" "):
                    recording = not recording
                    if not recording:
                        break
                time.sleep(0.01)

        if audio_buffer:
            return np.concatenate(audio_buffer, axis=0)
        return np.empty((0,), dtype=np.float32)

    def record_audio() -> np.ndarray:
        return curses.wrapper(_record_audio)

    class AudioPlayer:
        def __enter__(self):
            self.stream = sd.OutputStream(samplerate=24000, channels=1, dtype=np.int16)
            self.stream.start()
            return self

        def __exit__(self, exc_type, exc, tb):
            self.stream.stop()
            self.stream.close()

        def add_audio(self, audio_data: np.ndarray) -> None:
            self.stream.write(audio_data)


class TranscriptCallbacks(SingleAgentWorkflowCallbacks):
    def __init__(self) -> None:
        self.transcript: list[str] = []
        self.responses: list[str] = []

    def on_run(self, workflow: SingleAgentVoiceWorkflow, transcription: str) -> None:
        self.transcript.append(f"Human: {transcription}")


async def summarize(text: str) -> tuple[str, str]:
    prompt = (
        "Summarize the following standup meeting transcript and extract any action "
        "items for Apoorv. Respond in JSON with keys 'summary' and 'action_items'.\n\n"
        + text
    )
    completion = await openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content, prompt


def send_email(to_addr: str, body: str, subject: str = "Standup Summary") -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    if not user or not password:
        raise RuntimeError("SMTP_USERNAME and SMTP_PASSWORD environment variables required")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr

    with smtplib.SMTP_SSL(host, port) as smtp:
        smtp.login(user, password)
        smtp.sendmail(user, [to_addr], msg.as_string())


async def main() -> None:
    update_text = (
        "Yesterday I refactored the API integration. Today I will work on unit tests. "
        "No blockers."
    )
    agent = Agent(
        name="Digital Twin",
        instructions=(
            "You are Apoorv's digital twin in a standup meeting. "
            "When asked for an update, provide the following update verbatim:\n"
            f"{update_text}\n"
            "After giving the update, say you will keep listening."
        ),
        model="gpt-4o-mini",
    )

    callbacks = TranscriptCallbacks()
    workflow = SingleAgentVoiceWorkflow(agent, callbacks=callbacks)
    pipeline = VoicePipeline(workflow=workflow)

    print("Record your standup audio clip")
    audio = record_audio()
    result = await pipeline.run(AudioInput(buffer=audio))

    with AudioPlayer() as player:
        async for event in result.stream():
            if event.type == "voice_stream_event_audio":
                player.add_audio(event.data)

    callbacks.responses.append(result.total_output_text)
    callbacks.transcript.append(f"Agent: {result.total_output_text}")

    transcript_text = "\n".join(callbacks.transcript)
    summary, _ = await summarize(transcript_text)

    email_body = (
        "Meeting Transcript:\n\n" + transcript_text + "\n\n" + summary
    )
    send_email("apoorv.c2@gmail.com", email_body)
    print("Email sent with meeting summary and action items.")


if __name__ == "__main__":
    asyncio.run(main())
