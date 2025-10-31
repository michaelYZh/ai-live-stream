## AI Live Stream Backend

This FastAPI service powers an AI-driven livestream experience. It:

- Manages chat messages, superchats, and gifts in Redis-backed queues.
- Generates persona-specific audio clips and follow-up scripts using Boson AI models.
- Coordinates scripted content and interrupt handling (superchats or gifts) for a realtime stream loop.

Persona metadata (reference audio, transcripts, and scene descriptions) lives under `assets/personas`, so adding new voices only requires updating those assets and the accompanying JSON manifest.

---

## Prerequisites

- [Python](https://www.python.org/downloads/) available on your system (project is managed with [uv](https://docs.astral.sh/uv/) for env + dependency management).
- [Redis](https://redis.io/) running locally (default URL: `redis://localhost:6379/0`).
- Boson API credentials (multi-key string for rotation support).

---

## Setup

1. **Install Redis**
   ```sh
   brew install redis   # macOS example; use your platform's package manager or installer
   ```

2. **Install uv**
   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   (Or follow the official uv installation instructions for your platform.)

3. **Create a `.env` file**
   ```env
   BOSON_API_KEYS=key1,key2
   ```
   Adjust any values as needed; additional options are documented in `config.py`.

4. **Sync dependencies (creates `.venv` automatically)**
   ```sh
   uv sync
   ```

---

## Running the Backend

Start Redis (if not already running) and launch the FastAPI app:
```sh
brew services start redis   # macOS launchd example; use your platform's equivalent (e.g., redis-server on Windows/Linux)
uv run uvicorn app:app --reload
```

This starts the streaming processor and exposes REST endpoints (see `routers/`).

---

## Quick API Smoke Test

List generated audio chunks (empty by default):
```sh
curl "http://localhost:8000/api/v1/audio"
```

Trigger a superchat interrupt (replace persona/message as needed):
```sh
curl -X POST "http://localhost:8000/api/v1/audio/interrupt" \
     -H "Content-Type: application/json" \
     -d '{"kind": "superchat", "persona": "speed", "message": "Hyped to be here!"}'
```
