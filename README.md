# Digital Twin Voice Agent

This repository contains a minimal example of using the `openai-agents` SDK to create a voice agent that can act as a digital twin during stand‑up meetings. The agent will:

1. Listen to your audio input.
2. Provide a mocked stand‑up update on your behalf.
3. Capture the meeting transcript.
4. Summarize the transcript and extract action items.
5. Email the transcript and summary to `apoorv.c2@gmail.com`.

## Requirements

- Python 3.11+
- The `openai-agents` package with voice extras:
  ```bash
  pip install 'openai-agents[voice]'
  ```
- A Gmail (or other SMTP) account for sending the email. Set the following environment variables before running:
  - `SMTP_USERNAME` – your email address
  - `SMTP_PASSWORD` – your email password or app token
  - Optional: `SMTP_HOST` and `SMTP_PORT` if not using Gmail

## Usage

Run the script and follow the prompt to record your stand‑up audio clip:

```bash
python digital_twin_voice_agent.py
```

After the audio finishes processing, the script will send an email with the meeting transcript, summary, and action items.

The stand‑up update spoken by the agent is mocked inside `digital_twin_voice_agent.py` and can be modified as needed.
