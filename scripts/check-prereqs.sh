#!/bin/bash
set -e
MISSING=()

command -v python3 >/dev/null 2>&1 || MISSING+=("python3 (>=3.10): brew install python@3.12")
command -v node >/dev/null 2>&1 || MISSING+=("node (>=22): mise install node@22")
command -v pnpm >/dev/null 2>&1 || MISSING+=("pnpm: npm install -g pnpm")
command -v uv >/dev/null 2>&1 || MISSING+=("uv: brew install uv")
command -v ffmpeg >/dev/null 2>&1 || MISSING+=("ffmpeg: brew install ffmpeg")
command -v yt-dlp >/dev/null 2>&1 || MISSING+=("yt-dlp: brew install yt-dlp")

if [ ${#MISSING[@]} -gt 0 ]; then
  MSG="Missing prerequisites:\n"
  for m in "${MISSING[@]}"; do
    MSG+="  - $m\n"
  done
  MSG+="\nInstalling..."

  echo "{\"systemMessage\": \"$(echo -e "$MSG")\"}"

  command -v python3 >/dev/null 2>&1 || brew install python@3.12
  command -v node >/dev/null 2>&1 || mise install node@22
  command -v pnpm >/dev/null 2>&1 || npm install -g pnpm
  command -v uv >/dev/null 2>&1 || brew install uv
  command -v ffmpeg >/dev/null 2>&1 || brew install ffmpeg
  command -v yt-dlp >/dev/null 2>&1 || brew install yt-dlp
fi
