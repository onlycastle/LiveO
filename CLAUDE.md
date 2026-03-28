# LiveO

Live streaming highlight extraction platform.

## Prerequisites

Run the check below on session start. Install anything missing.

```bash
#!/bin/bash
set -e
MISSING=()

command -v python3 >/dev/null || MISSING+=("python3 (>=3.10): brew install python@3.12")
command -v node >/dev/null || MISSING+=("node (>=22): mise install node@22")
command -v pnpm >/dev/null || MISSING+=("pnpm: npm install -g pnpm")
command -v uv >/dev/null || MISSING+=("uv: brew install uv")
command -v ffmpeg >/dev/null || MISSING+=("ffmpeg: brew install ffmpeg")
command -v yt-dlp >/dev/null || MISSING+=("yt-dlp: brew install yt-dlp")

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "Missing prerequisites:"
  printf '  - %s\n' "${MISSING[@]}"
  echo ""
  echo "Installing..."
  command -v python3 >/dev/null || brew install python@3.12
  command -v node >/dev/null || mise install node@22
  command -v pnpm >/dev/null || npm install -g pnpm
  command -v uv >/dev/null || brew install uv
  command -v ffmpeg >/dev/null || brew install ffmpeg
  command -v yt-dlp >/dev/null || brew install yt-dlp
fi
```

| Tool | Min Version | Purpose |
|------|-------------|---------|
| Python | 3.10+ | Backend (FastAPI, uvicorn) |
| Node.js | 22+ | Frontend (Next.js 16, React 19) |
| pnpm | latest | Frontend package manager |
| uv | latest | Python package manager |
| ffmpeg | 7+ | Video capture & segment extraction |
| yt-dlp | latest | Live stream URL resolution |

### Python deps install

```bash
uv pip install -e ".[dev,stt]"
```

### Frontend deps install

```bash
cd frontend && pnpm install
```

## Running

```bash
# Backend
uvicorn backend.server:app --reload

# Frontend
cd frontend && pnpm dev
```

## Project Structure

- `backend/` — FastAPI server, capture pipeline, VAD, STT
- `frontend/` — Next.js 16 app (React 19, Tailwind 4)
- `tests/` — pytest test suite
