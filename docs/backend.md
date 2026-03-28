# backend.md — 라이브 스트리밍 캡처 모듈 설계

**담당:** Seongheum
**상위 문서:** PRD.md

---

## 1. 목표

라이브 스트리밍 영상을 실시간 파이프라인으로 캡처하여, 후속 모듈(Transcription, Highlight Detection)에 영상/오디오 데이터를 실시간으로 공급한다.

## 2. 캡처 방식

| 방식 | 용도 | 지연 시간 | 비고 |
|------|------|-----------|------|
| **OBS RTMP 수신** | **Production** | 16~33ms | 스트리머 본인이 OBS에서 동시 송출 |
| **yt-dlp --live-from-start** | **Demo only** | 2~4초 | YouTube ToS 위반 → 시연 목적만 |

> **⚠️ YouTube ToS:** yt-dlp를 이용한 YouTube 스트림 캡처는 ToS 위반이므로 데모에만 사용한다. 실제 사용자는 스트리머 본인이므로 OBS에서 RTMP로 본 시스템에 동시 송출하는 구조로 설명한다.

## 3. 시스템 아키텍처

### 3.1 Production: OBS RTMP 수신

```
OBS Studio
  ├──→ YouTube (RTMP ingest) — 실제 방송
  └──→ Our Server (rtmp://localhost:1935/live/stream) — 하이라이트 추출
         │
         ▼
   nginx-rtmp (RTMP 서버)
         │
         ▼
   ffmpeg demux (실시간 파이프)
    ├──→ Video pipe (H.264) → KillFeed OCR + Ring Buffer 저장
    └──→ Audio pipe (PCM 16kHz mono) → VAD → STT
                                      └──→ Audio Excitement Detection
```

### 3.2 Demo: yt-dlp

```
YouTube Live Stream
       │
       ▼
  yt-dlp --live-from-start (stdout pipe)
       │
       ▼
  ffmpeg demux (실시간 파이프)
   ├──→ Video pipe
   └──→ Audio pipe
```

## 4. 핵심 컴포넌트

### 4.1 RTMPStreamCapture (Production)

```python
import subprocess

class RTMPStreamCapture:
    def __init__(self, rtmp_url: str = "rtmp://localhost:1935/live/stream"):
        self.rtmp_url = rtmp_url
        self.video_pipe = None
        self.audio_pipe = None

    def start(self) -> None:
        """OBS RTMP 스트림을 수신하여 video/audio 파이프로 분리"""
        self.video_pipe = subprocess.Popen(
            ["ffmpeg", "-i", self.rtmp_url,
             "-f", "mpegts", "-c:v", "copy", "-an", "pipe:1"],
            stdout=subprocess.PIPE
        )
        self.audio_pipe = subprocess.Popen(
            ["ffmpeg", "-i", self.rtmp_url,
             "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
             "-f", "wav", "pipe:1"],
            stdout=subprocess.PIPE
        )

    def stop(self) -> None:
        for p in [self.video_pipe, self.audio_pipe]:
            if p:
                p.terminate()

    def is_alive(self) -> bool:
        return all(p and p.poll() is None
                   for p in [self.video_pipe, self.audio_pipe])
```

### 4.2 YtdlpDemoCapture (Demo)

```python
class YtdlpDemoCapture:
    def __init__(self, video_url: str):
        self.video_url = video_url
        self.process = None

    def start(self) -> None:
        """yt-dlp --live-from-start로 스트림 캡처 (demo only)"""
        self.process = subprocess.Popen(
            ["yt-dlp", self.video_url,
             "--live-from-start",
             "-f", "bestvideo[height<=1080]+bestaudio",
             "--downloader", "ffmpeg",
             "--hls-use-mpegts",
             "--fragment-retries", "50",
             "--retries", "10",
             "-o", "pipe:"],
            stdout=subprocess.PIPE
        )
        # stdout을 ffmpeg에 연결하여 video/audio 분리
```

### 4.3 RingBuffer

실시간 영상을 ring buffer로 저장하여, 하이라이트 감지 시 과거 영상을 클리핑할 수 있게 한다.

```python
class RingBuffer:
    def __init__(self, max_duration_sec: int = 300):
        """최근 5분(300초) 분량의 영상을 순환 저장"""
        self.max_duration = max_duration_sec
        self.segments = []  # [(timestamp, file_path), ...]

    def add_segment(self, timestamp: float, path: str) -> None:
        self.segments.append((timestamp, path))
        self._cleanup()

    def get_range(self, start: float, end: float) -> list[str]:
        """특정 시간 범위의 세그먼트 파일 목록 반환"""
        return [p for t, p in self.segments if start <= t <= end]

    def _cleanup(self) -> None:
        """오래된 세그먼트 삭제"""
        ...
```

## 5. 출력 인터페이스

### 5.1 데이터 규격

| 항목 | 규격 |
|------|------|
| 영상 파이프 | MPEG-TS, H.264 코덱 (실시간 stdout) |
| 오디오 파이프 | PCM 16-bit, 16kHz, mono (실시간 stdout) |
| Ring Buffer | 최근 5분 분량의 .ts 세그먼트 파일 |

### 5.2 이벤트 인터페이스

```python
from dataclasses import dataclass
from enum import Enum

class StreamEvent(Enum):
    STREAM_STARTED = "stream_started"
    SEGMENT_READY = "segment_ready"
    AUDIO_READY = "audio_ready"
    STREAM_ERROR = "stream_error"

@dataclass
class SegmentReadyEvent:
    event: StreamEvent
    video_path: str
    audio_path: str
    timestamp_start: float
    timestamp_end: float
    duration: float
```

## 6. 의존성

- **nginx-rtmp** (production RTMP 서버)
- **yt-dlp** ≥ 2024.01.01 (demo)
- **ffmpeg** ≥ 6.0
- **Python** ≥ 3.10

## 7. 테스트 계획

| 테스트 항목 | 방법 | 성공 기준 |
|-------------|------|-----------|
| OBS RTMP 수신 | OBS → 로컬 RTMP 10분 | 끊김 없이 pipe 생성 |
| yt-dlp demo | --live-from-start 캡처 | stdout pipe 정상 출력 |
| 실시간 파이프라인 | pipe → ffmpeg demux | video/audio 분리 정상 |
| Ring Buffer | 5분 초과 시 cleanup | 오래된 세그먼트 자동 삭제 |
| 장시간 안정성 | 2시간 연속 | 메모리 누수 없음 |
