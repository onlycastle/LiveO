# Backend

라이브 스트리밍 캡처 + 실시간 하이라이트 추출 백엔드.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 외부 의존성

- **ffmpeg** >= 6.0
- **yt-dlp** (demo 모드)

```bash
brew install ffmpeg yt-dlp
```

## 실행

### Demo 모드 (Twitch/YouTube 라이브)

```bash
PYTHONPATH=. python -m backend --mode demo --url <LIVE_URL> --output-dir ./segments
```

```bash
# Twitch
PYTHONPATH=. python -m backend --mode demo --url https://www.twitch.tv/채널명

# YouTube
PYTHONPATH=. python -m backend --mode demo --url https://www.youtube.com/watch?v=VIDEO_ID
```

### RTMP 모드 (Production)

```bash
PYTHONPATH=. python -m backend --mode rtmp --url rtmp://localhost:1935/live/stream
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--mode` | `demo` | `demo` (yt-dlp) 또는 `rtmp` |
| `--url` | - | 스트림 URL (demo: 필수) |
| `--segment-duration` | `5.0` | 세그먼트 길이 (초) |
| `--buffer-duration` | `300` | Ring Buffer 최대 저장 시간 (초) |
| `--output-dir` | 임시 디렉토리 | 세그먼트 저장 경로 |

## 테스트

### 유닛 테스트

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

### 스트리밍 통합 테스트

실제 라이브 스트림에 연결하여 캡처 파이프라인 전체를 검증한다.

```bash
PYTHONPATH=. python backend/test_stream.py <LIVE_URL> [--duration 15] [--segment-duration 5]
```

```bash
# Twitch 테스트
PYTHONPATH=. python backend/test_stream.py https://www.twitch.tv/채널명

# YouTube 테스트
PYTHONPATH=. python backend/test_stream.py https://www.youtube.com/watch?v=VIDEO_ID --duration 20
```

검증 항목 (20개):

| 단계 | 검증 내용 |
|------|-----------|
| URL 해석 | yt-dlp로 스트림 URL 추출 성공, HTTP URL 유효성 |
| 파이프라인 실행 | ffmpeg 프로세스 시작, 지정 시간 동안 캡처 |
| 세그먼트 생성 | 파일 생성 수, 이벤트/RingBuffer 일치, duration > 0 |
| 영상 품질 | H.264 코덱, >= 1280x720, >= 30fps, 숏폼 품질(1080p) 확인 |
| 정리 | 임시 파일 자동 삭제 |

## 문서

- [backend.md](docs/backend.md) — 서버 전체 개요 + 역할 분담
- [streaming.md](docs/streaming.md) — 스트림 캡처 설계 (Seongheum)
- [transcript.md](docs/transcript.md) — STT + 하이라이트 감지 (Sungman)
- [editing.md](docs/editing.md) — 클립 편집 + 템플릿 (Sungman)
