# Chatterbox TTS - Home Assistant Integration

Custom Home Assistant integration for [Chatterbox TTS Server](https://github.com/devnen/Chatterbox-TTS-Server), providing text-to-speech with voice cloning capabilities.

## Features

- Built-in voice selection from your server's voice library
- Voice cloning from reference audio
- Configurable temperature, exaggeration, CFG weight, seed, and speed
- Server health monitoring sensor
- HA service calls for TTS generation

## Installation (HACS)

1. Add this repository as a custom repository in HACS
2. Install "Chatterbox TTS"
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services → Add Integration → "Chatterbox TTS Client"

## Configuration

During setup you'll be prompted for:

- **Host**: IP address of your Chatterbox TTS server
- **Port**: Server port (default: 8000)
- **Voice**: Default voice to use
- **Temperature**: Controls randomness (0.0-1.0)
- **Exaggeration**: Controls expressiveness (0.0-2.0)
- **CFG Weight**: Classifier-free guidance weight (0.0-1.0)
- **Seed**: Random seed (0 = random)
- **Speed Factor**: Speech speed (0.5-2.0)

## Requirements

- **[Chatterbox TTS Server](https://github.com/devnen/Chatterbox-TTS-Server)** — this integration requires the devnen/Chatterbox-TTS-Server backend running and accessible on your network
