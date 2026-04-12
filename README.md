# Chatterbox TTS - Home Assistant Integration

Custom Home Assistant integration for [Chatterbox TTS Server](https://github.com/devnen/Chatterbox-TTS-Server), providing text-to-speech capabilities.

## Features

- Voice selection dynamically populated from your server's voice library
- Configurable temperature, exaggeration, CFG weight, seed, and speed
- Server health monitoring sensor

## Installation (HACS)

1. Add this repository as a custom repository in HACS
2. Install "Chatterbox TTS Client"
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services → Add Integration → "Chatterbox TTS Client"

## Configuration

Setup is two steps:

**Step 1 — Connect to server:**
- **Host**: IP address of your Chatterbox TTS server
- **Port**: Server port (default: 8000)
- **Name**: Display name for the integration

**Step 2 — Voice and settings** (voice list is fetched live from your server):
- **Voice**: Default voice to use
- **Temperature**: Controls randomness (0.0-1.0)
- **Exaggeration**: Controls expressiveness (0.0-2.0)
- **CFG Weight**: Classifier-free guidance weight (0.0-1.0)
- **Seed**: Random seed (0 = random)
- **Speed Factor**: Speech speed (0.5-2.0)

## Requirements

- **[Chatterbox TTS Server](https://github.com/devnen/Chatterbox-TTS-Server)** — this integration requires the devnen/Chatterbox-TTS-Server backend running and accessible on your network
