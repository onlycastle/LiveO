# streaming.md — 라이브 스트리밍 캡처 모듈 설계

**담당:** Seongheum
**상위 문서:** [backend.md](backend.md)

---

## 1. 목표

라이브 스트리밍 영상을 실시간 파이프라인으로 캡처하여, 후속 모듈(Transcription, Highlight Detection)에 영상/오디오 데이터를 실시간으로 공급한다.

## 2. 캡처 방식

| 방식 | 용도 | 지연 시간 | 비고 |
|------|------|-----------|------|
| **OBS RTMP 수신** | **Production** | 16~33ms | 스트리머 본인이 OBS에서 동시 송출 |
| **yt-dlp --get-url → ffmpeg** | **Demo only** | 2~4초 | YouTube/Twitch ToS 위반 → 시연 목적만 |

> **⚠️ ToS:** yt-dlp를 이용한 스트림 캡처는 ToS 위반이므로 데모에만 사용한다. 실제 사용자는 스트리머 본인이므로 OBS에서 RTMP로 본 시스템에 동시 송출하는 구조로 운영한다.

## 3. 시스템 아키텍처

### 3.1 Production: OBS RTMP 수신

```
OBS Studio
  ├──→ YouTube/Twitch (RTMP ingest) — 실제 방송
  └──→ Our Server (rtmp://localhost:1935/live/stream) — 하이라이트 추출
         │
         ▼
   nginx-rtmp (RTMP 서버)
         │
         ▼
   ffmpeg demux (단일 프로세스, dual output)
    ├──→ video.ts (named FIFO) → KillFeed OCR + Ring Buffer 저장
    └──→ audio.wav (named FIFO) → VAD → STT
                                 └──→ Audio Excitement Detection
```

### 3.2 Demo: yt-dlp

```
YouTube/Twitch Live Stream
       │
       ▼
  yt-dlp --get-url (스트림 URL 추출)
       │
       ▼
  ffmpeg -i <stream_url> (단일 프로세스, dual output)
   ├──→ video.ts (named FIFO)
   └──→ audio.wav (named FIFO)
```

## 4. 핵심 컴포넌트

### 4.1 RTMPStreamCapture (Production)

- 단일 ffmpeg 프로세스로 RTMP 입력을 video/audio named FIFO로 분리
- 임시 디렉토리에 FIFO 생성, stop 시 자동 정리

### 4.2 YtdlpDemoCapture (Demo)

- `yt-dlp --get-url`로 HLS/DASH 스트림 URL 추출
- ffmpeg가 직접 스트림 URL을 읽어 named FIFO로 출력
- YouTube, Twitch 등 yt-dlp 지원 플랫폼 모두 호환

### 4.3 RingBuffer

실시간 영상을 ring buffer로 저장하여, 하이라이트 감지 시 과거 영상을 클리핑할 수 있게 한다.

- 최근 5분(300초) 분량의 .ts 세그먼트 파일 순환 저장
- 시간 범위 기반 세그먼트 조회
- 만료 세그먼트 자동 삭제

### 4.4 Pipeline

- Capture + RingBuffer + 이벤트 디스패치를 통합 관리
- 설정 가능한 세그먼트 길이 (기본 5초)
- 콜백 기반 이벤트 알림 (`on_segment`)

## 5. 출력 인터페이스

### 5.1 데이터 규격

| 항목 | 규격 |
|------|------|
| 영상 파이프 | MPEG-TS, H.264 코덱 (named FIFO) |
| 오디오 파이프 | PCM 16-bit, 16kHz, mono (named FIFO) |
| Ring Buffer | 최근 5분 분량의 .ts 세그먼트 파일 |

### 5.2 이벤트 인터페이스

```python
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
| yt-dlp demo | Twitch/YouTube 라이브 캡처 | 세그먼트 정상 생성 |
| 실시간 파이프라인 | ffmpeg demux → named FIFO | video/audio 분리 정상 |
| Ring Buffer | 5분 초과 시 cleanup | 오래된 세그먼트 자동 삭제 |
| 장시간 안정성 | 2시간 연속 | 메모리 누수 없음 |
