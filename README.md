# Chatterbox TTS Client for Home Assistant

A Home Assistant integration for [Chatterbox TTS Server](https://github.com/devnen/Chatterbox-TTS-Server), providing high-quality text-to-speech with full control over generation parameters. Works with automations, assistants, scripts, or any HA component that supports TTS.

## Features

- **Text-to-Speech** via your self-hosted Chatterbox TTS server
- **Multi-language support** – 54 languages available in HA Assist pipeline settings
- **Dynamic voice loading** – Voices are fetched directly from your server
- **Generation parameters** – Fine-tune output with temperature, exaggeration, CFG weight, and seed
- **TTS Streaming** – Low-latency streaming support (HA 2025.7+)
- **TTS agent profiles** – Create multiple profiles with different voice/generation settings via sub-entries
- **`chatterbox_tts.say` service** – Full-featured service with voice, speed, temperature, exaggeration, CFG weight, seed, volume, and media pause/resume
- **Volume restoration** – Automatically restores speaker volumes after TTS announcements
- **Media pause/resume** – Pauses currently playing media during announcements and resumes afterward
- **WAV audio support** – WAV responses are auto-converted to MP3
- **Optional API key** – API key supported for secured servers, optional for local use
- **Reconfigure & reauth** – Change server URL or API key without recreating entities
- **Precise audio duration detection** – Improved timing for TTS playback synchronization
- **Diagnostics** – Built-in diagnostics support for troubleshooting

## `chatterbox_tts.say` Service

```yaml
service: chatterbox_tts.say
target:
  entity_id: media_player.living_room_speaker
data:
  tts_entity: tts.chatterbox_tts_my_voice
  message: "Hello from Chatterbox!"
  voice: narrator          # Override default voice
  speed: 1.0               # Speech speed (0.25–4.0)
  temperature: 0.8         # Randomness (0.0–1.5)
  exaggeration: 0.7        # Expressiveness (0.25–2.0)
  cfg_weight: 0.5          # CFG guidance (0.2–1.0)
  seed: 0                  # 0 = random
  volume: 0.6              # Announcement volume (0.0–1.0)
  pause_playback: true     # Pause media during announcement
```

## HACS Installation

1. Add this repository as a custom repository in HACS
2. Search for **Chatterbox TTS Client** and install
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services → Add Integration → Chatterbox TTS Client**
5. Enter your server URL (e.g. `http://localhost:8000/v1/audio/speech`) and optional API key

## Manual Installation

1. Copy the `chatterbox_tts_client` folder to `config/custom_components/chatterbox_tts/`
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & Services → Add Integration → Chatterbox TTS Client**
