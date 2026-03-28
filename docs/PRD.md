# PRD: Valorant Live Streaming Shortform Highlight Extractor

## 1. Overview

Valorant 라이브 스트리밍 중 하이라이트 구간을 실시간으로 감지하고, 숏폼 콘텐츠(TikTok, YouTube Shorts, Instagram Reels)용 vertical video(9:16)로 자동 추출하는 시스템.

## 2. Problem Statement

Valorant 스트리머가 라이브 방송 후 하이라이트를 수동으로 편집하는 과정은 시간이 많이 걸리고, 숏폼 플랫폼에 최적화된 세로 영상으로의 변환까지 추가 작업이 필요하다. 이 프로세스를 자동화하여 스트리머가 방송에 집중하면서도 숏폼 콘텐츠를 빠르게 생산할 수 있도록 한다.

## 3. Scope & Constraints

| 항목 | 결정 사항 |
|------|-----------|
| 대상 게임 | **Valorant만** 고려 |
| 언어 | **영어만** 지원 |
| 처리 방식 | **실시간 처리** 우선 |
| UI | **Web View** (Python 서버 백엔드) |
| 테마 | **다크 모드 전용** |
| 게임 성능 | 고려하지 않음 (별도 머신 또는 보조 모니터 사용 가정) |

## 4. Target Platforms

- TikTok
- YouTube Shorts
- Instagram Reels

## 5. Output Specifications

| 항목 | 값 |
|------|-----|
| 길이 | 15초 ~ 30초 |
| 영상 비율 | 9:16 (vertical video) |
| 해상도 | 1080x1920 |
| 코덱 | H.264 (video), AAC (audio) |
| 포맷 | .mp4 |

---

## 6. System Architecture

### 6.1 전체 파이프라인

```
OBS Studio (RTMP 송출)
       │
       ▼
┌──────────────────────────────────────────────────┐
│              Python Backend Server                │
│                                                  │
│  ┌────────────┐                                  │
│  │ Live Server │  OBS RTMP 수신 (production)     │
│  │ (Seongheum) │  yt-dlp --live-from-start (demo)│
│  └─────┬──────┘                                  │
│        │ real-time pipe (stdout → stdin)          │
│        ├──────────────┬──────────────────┐       │
│        ▼              ▼                  ▼       │
│     Video          Audio              Audio      │
│    (H.264)        (PCM 16kHz)        (raw)       │
│        │              │                  │       │
│        │              ▼                  ▼       │
│        │     ┌──────────────┐   ┌─────────────┐ │
│        │     │ Transcription │   │   Audio      │ │
│        │     │ (Sungman)     │   │  Excitement  │ │
│        │     │ Silero VAD    │   │  Detector    │ │
│        │     │ + STT Engine  │   └──────┬──────┘ │
│        │     └──────┬───────┘          │        │
│        │            │                   │        │
│        │            ▼                   │        │
│        │     KeywordDetector            │        │
│        │            │                   │        │
│        ▼            ▼                   ▼        │
│  KillFeedDetector   │                   │        │
│  (Valorant OCR)     │                   │        │
│        │            │                   │        │
│        └────────────┼───────────────────┘        │
│                     ▼                            │
│            HighlightAggregator                   │
│            (score >= 0.6 → clip)                 │
│                     │                            │
│                     ▼                            │
│              ClipEditor                          │
│              (ffmpeg 16:9→9:16)                  │
│                     │                            │
│                     ▼                            │
│           highlight_*.mp4 (9:16)                 │
│                                                  │
│  ┌──────────────────────────────────────┐       │
│  │  WebSocket (실시간 이벤트 push)        │       │
│  └──────────────────────────────────────┘       │
└──────────────────────────────────────────────────┘
       │
       ▼ (HTTP + WebSocket)
┌──────────────────────────────────────────────────┐
│              Web UI (Jemin)                       │
│              Dark mode only                      │
│              브라우저에서 접속                      │
└──────────────────────────────────────────────────┘
```

---

## 7. Module Details

### 7.1 Live Stream Capture (담당: Seongheum)

라이브 스트리밍 영상을 실시간으로 캡처하여, 실시간 파이프라인을 통해 후속 모듈에 영상/오디오 데이터를 공급한다.

#### 캡처 방식

| 방식 | 용도 | 지연 시간 | 비고 |
|------|------|-----------|------|
| **OBS RTMP 수신** | **Production** | 16~33ms | 스트리머 본인이 사용자이므로 OBS에서 직접 송출 |
| **yt-dlp --live-from-start** | **Demo only** | 2~4초 | YouTube ToS 위반 → 시연 목적에만 사용 |

> **⚠️ YouTube ToS 참고:** YouTube 스트림을 yt-dlp로 캡처하는 것은 YouTube 서비스 약관 위반이다. 실제 서비스에서는 사용자(스트리머 본인)가 OBS에서 RTMP로 본 시스템에 동시 송출하는 구조로 운영한다. yt-dlp는 데모/개발 시에만 사용한다.

#### Production: OBS RTMP 수신

스트리머가 OBS에서 YouTube + 본 시스템 두 곳에 동시 송출하는 구조.

```
OBS Studio
  ├──→ YouTube (RTMP ingest) — 실제 방송
  └──→ Our Server (RTMP ingest) — 하이라이트 추출용
```

```python
# RTMP 수신 후 ffmpeg로 실시간 파이프라인 구성
class RTMPStreamCapture:
    def start(self, rtmp_url: str = "rtmp://localhost:1935/live/stream") -> None:
        """OBS에서 송출하는 RTMP 스트림을 수신하여 파이프라인에 연결"""
        self.video_pipe = subprocess.Popen(
            ["ffmpeg", "-i", rtmp_url,
             "-f", "mpegts", "-c:v", "copy", "-an", "pipe:1"],
            stdout=subprocess.PIPE
        )
        self.audio_pipe = subprocess.Popen(
            ["ffmpeg", "-i", rtmp_url,
             "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
             "-f", "wav", "pipe:1"],
            stdout=subprocess.PIPE
        )
```

#### Demo: yt-dlp --live-from-start

```bash
yt-dlp "https://www.youtube.com/watch?v=VIDEO_ID" \
  --live-from-start \
  -f "bestvideo[height<=1080]+bestaudio" \
  --downloader ffmpeg \
  --hls-use-mpegts \
  --fragment-retries 50 \
  --retries 10 \
  -o "pipe:" | ffmpeg -i pipe:0 ...
```

#### 실시간 파이프라인

파일 기반 중간 저장 대신, **stdout → stdin 파이프** 방식으로 실시간 스트리밍 처리한다.

```
RTMP/yt-dlp → ffmpeg demux ─┬─ video pipe → KillFeed OCR + 클립 저장 (ring buffer)
                             └─ audio pipe → VAD → STT → Keyword Detection
                                           └───→ Audio Excitement Detection
```

#### 출력 인터페이스

```python
@dataclass
class SegmentReadyEvent:
    event: str              # "segment_ready" | "audio_ready" | "stream_error"
    video_path: str         # ring buffer 내 영상 경로
    audio_path: str         # 오디오 청크 경로
    timestamp_start: float  # 스트림 시작 기준 (초)
    timestamp_end: float
    duration: float
```

#### 의존성
- **yt-dlp** ≥ 2024.01.01 (demo 모드)
- **ffmpeg** ≥ 6.0
- **nginx-rtmp** 또는 동급 RTMP 서버 (production 모드)
- **Python** ≥ 3.10

#### 테스트 계획

| 테스트 항목 | 방법 | 성공 기준 |
|-------------|------|-----------|
| OBS RTMP 수신 | OBS에서 로컬 RTMP 송출 후 10분 캡처 | 끊김 없이 video/audio pipe 생성 |
| yt-dlp demo 캡처 | --live-from-start로 실제 YouTube 라이브 캡처 | .ts 스트림 정상 출력 |
| 실시간 파이프라인 | pipe stdout → ffmpeg stdin 연결 | 오디오 추출 16kHz mono WAV 확인 |
| 장시간 안정성 | 2시간 연속 캡처 | 메모리 누수 없음, pipe 정상 |

---

### 7.2 Transcription + Highlight Detection + Editing (담당: Sungman)

스트리밍 오디오를 실시간으로 텍스트 변환(STT)하고, 멀티시그널 기반으로 하이라이트를 감지하여 9:16 vertical clip으로 편집한다.

#### A. Transcription

**STT 엔진 비교 (영어 기준)**

| 엔진 | 지연 시간 | 비용 | 비고 |
|------|-----------|------|------|
| **Deepgram Nova-3** | <300ms | $0.46/hr | **추천: 최저 지연** |
| Google Cloud STT | <500ms | $0.006~0.024/15s | 문서 풍부 |
| WhisperKit (로컬) | ~460ms | 무료 | GPU 필요, **비용 최적 대안** |
| faster-whisper (로컬) | ~500ms+ | 무료 | CPU 가능 |

**실시간 파이프라인:**
```
Audio Pipe → Silero VAD (<1ms) → Deepgram Streaming API (<300ms) → TranscriptSegment
```

**Silero VAD** — 게임 오디오에서 음성 구간만 선별:
- 정확도: 87.7% TPR at 5% FPR
- 처리 속도: 30ms 청크당 <1ms
- 모델 크기: 1.8MB

**오디오 소스 분리 (Optional, MVP 제외):**
Demucs로 보컬 분리 가능 (100~500ms 추가 지연). STT 정확도 이슈 발생 시 적용.

**출력 데이터:**
```python
@dataclass
class TranscriptSegment:
    text: str              # 인식된 텍스트
    start_time: float      # 스트림 기준 시작 시간 (초)
    end_time: float
    confidence: float      # 0.0 ~ 1.0
    language: str = "en"   # 영어 고정
    is_speech: bool = True
```

#### B. Highlight Detection (Multi-Signal)

| 신호 | 가중치 | 감지 방법 | 지연 |
|------|--------|-----------|------|
| **오디오 흥분도** | 0.3 | 음량 급증 + 음성 피치 변화 (EMA 기반선 대비 spike 감지) | <100ms |
| **키워드 매칭** | 0.3 | Transcript에서 감탄사/게임 용어 탐지 | STT 지연에 종속 |
| **킬피드 OCR** | 0.4 | **Valorant 킬피드 영역** (우상단) 텍스트 인식 | ~200ms |

**Valorant 킬피드 OCR:**
- ROI: Valorant 킬피드 영역 고정 좌표 (우상단, 게임 해상도별 사전 정의)
- EasyOCR 또는 Tesseract로 킬 이벤트 텍스트 변화 감지

**키워드 목록 (영어):**
```python
HIGHLIGHT_KEYWORDS = [
    "oh my god", "insane", "clutch", "ace", "headshot",
    "let's go", "no way", "what", "nice", "one tap",
    "flawless", "thrifty", "team ace", "collateral"
]
```

**하이라이트 판정:**
```python
@dataclass
class HighlightCandidate:
    timestamp: float        # 스트림 기준 시간 (초)
    score: float            # 종합 점수 (0.0 ~ 1.0)
    audio_score: float
    keyword_score: float
    killfeed_score: float
    duration: float = 20.0  # 기본 클립 길이 (초)

# score = (audio × 0.3) + (keyword × 0.3) + (killfeed × 0.4)
# score >= 0.6 → 하이라이트 후보
```

#### C. Video Editing (16:9 → 9:16)

**MVP: FFmpeg 정적 중앙 크롭** — Valorant은 크로스헤어가 화면 중앙이므로 중앙 크롭이 효과적.

```bash
ffmpeg -i source.ts \
  -ss {start} -t {duration} \
  -vf "crop=608:1080:656:0,scale=1080:1920" \
  -c:v libx264 -crf 20 -preset medium \
  -c:a aac -b:a 128k \
  highlight_{timestamp}_{score}.mp4
```

**클리핑 규칙:**
- 하이라이트 시점 **5초 전**부터 시작
- 최소 15초, 최대 30초
- 파일명: `highlight_{timestamp}_{score}.mp4`

#### 의존성
- **Deepgram SDK** 또는 **faster-whisper** ≥ 1.0
- **Silero VAD** (torch hub)
- **ffmpeg** ≥ 6.0
- **EasyOCR** 또는 **Tesseract** (Valorant 킬피드 OCR)
- **Python** ≥ 3.10, **numpy**, **torch**

#### 테스트 계획

| 테스트 항목 | 방법 | 성공 기준 |
|-------------|------|-----------|
| STT 정확도 | 영어 Valorant 스트리밍 5분 샘플 | WER < 20% |
| VAD 정확도 | 게임 오디오 혼합 샘플 | 음성 구간 TPR > 85% |
| 킬피드 OCR | Valorant 킬피드 스크린샷 50장 | 킬 이벤트 감지율 > 80% |
| 하이라이트 감지 | 수동 레이블 20개 vs 자동 감지 | recall > 70%, precision > 60% |
| 9:16 크롭 | 생성 클립의 크로스헤어 위치 | 화면 중앙 30% 이내 |
| 클립 길이 | 전체 생성 클립 | 15~30초 범위 100% |

---

### 7.3 UI Design (담당: Jemin)

브라우저 기반 Web UI로, Python 서버와 HTTP/WebSocket으로 통신한다. **다크 모드 전용.**

#### 기술 스택

| 레이어 | 기술 | 근거 |
|--------|------|------|
| Backend | **Python** (FastAPI 또는 Flask) | 다른 모듈과 동일 언어, 통합 용이 |
| Frontend | HTML/CSS/JS 또는 React | Web View로 브라우저 접속 |
| 실시간 통신 | **WebSocket** | 하이라이트 실시간 push |
| 영상 재생 | HTML5 Video | .mp4 직접 재생 |
| 테마 | **다크 모드 전용** | — |

#### 화면 구성

**메인 대시보드:**
```
┌─────────────────────────────────────────────────────────┐
│  [Logo]  Highlight Extractor          [Settings]  DARK  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────┐  ┌──────────────────────────┐  │
│  │                     │  │  Highlights               │  │
│  │   Live Preview      │  │                          │  │
│  │   / VOD Player      │  │  ● 02:34 Kill (0.9)     │  │
│  │                     │  │  ● 05:12 Clutch (0.85)   │  │
│  │   [16:9 원본]       │  │  ○ 08:45 (0.55) — skip  │  │
│  │                     │  │  ● 12:01 Ace (0.95)      │  │
│  └─────────────────────┘  │  ...                     │  │
│                           └──────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ▶ ━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│  │  00:02:34 / 02:15:30       ▲ ▲   ▲     ▲  ▲    │   │
│  │                         (highlight markers)       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  [Start Stream]  [Stop Stream]  [Export Selected]       │
└─────────────────────────────────────────────────────────┘
```

**클립 편집 화면:**
```
┌─────────────────────────────────────────────────────────┐
│  ← Back                              Edit Clip          │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  원본 (16:9) │  │  Preview     │                     │
│  │              │  │  (9:16)      │                     │
│  └──────────────┘  └──────────────┘                     │
│                                                         │
│  Start: [02:29]  End: [02:54]  Duration: 25s            │
│  ┌──────────────────────────────────────────────────┐   │
│  │  [  ━━━━━━━━━━━━━━  ]  trim handles             │   │
│  └──────────────────────────────────────────────────┘   │
│  Crop: ○ Center  ○ Custom  ○ Split-screen              │
│                                                         │
│  [Cancel]                          [Save] [Export →]     │
└─────────────────────────────────────────────────────────┘
```

**내보내기 화면:**
```
┌─────────────────────────────────────────────────────────┐
│  Export Settings                                         │
├─────────────────────────────────────────────────────────┤
│  Selected clips: 3                                      │
│                                                         │
│  Platform:                                              │
│    ☑ TikTok     (1080x1920, ≤60s)                      │
│    ☑ YouTube Shorts  (1080x1920, ≤60s)                 │
│    ☑ Instagram Reels (1080x1920, ≤90s)                 │
│                                                         │
│  Output folder: ~/highlights/   [Change]                │
│  ☐ Include subtitles (from transcript)                  │
│                                                         │
│  [Cancel]                                  [Export]      │
└─────────────────────────────────────────────────────────┘
```

#### 백엔드 API 인터페이스

**스트림 제어 (REST):**
```
POST /api/stream/start   { "source": "obs" | "yt-dlp", "url": "..." }
POST /api/stream/stop
GET  /api/stream/status   → { "isLive", "elapsed", "captureMethod", "error" }
```

**하이라이트 (REST):**
```
GET    /api/highlights              → Highlight[]
PATCH  /api/highlights/{id}         → update status/duration
DELETE /api/highlights/{id}
POST   /api/highlights/export       { "ids": [...], "options": {...} }
```

**실시간 이벤트 (WebSocket):**
```
ws://server/ws/events

Server → Client:
  { "type": "highlight_detected", "data": Highlight }
  { "type": "stream_status", "data": StreamStatus }
  { "type": "transcript_update", "data": TranscriptSegment }
  { "type": "export_progress", "data": { "clipId", "percent" } }
```

**Highlight 데이터 구조:**
```json
{
  "id": "string",
  "timestamp": 154.2,
  "score": 0.9,
  "audioScore": 0.8,
  "keywordScore": 0.7,
  "killfeedScore": 1.0,
  "duration": 25,
  "thumbnailPath": "/static/thumbs/highlight_154_0.9.jpg",
  "clipPath": "/static/clips/highlight_154_0.9.mp4",
  "status": "detected | approved | excluded | exported"
}
```

#### 테스트 계획

| 테스트 항목 | 방법 | 성공 기준 |
|-------------|------|-----------|
| 하이라이트 목록 렌더링 | 100개 로드 | 1초 이내 |
| WebSocket 실시간 push | 새 하이라이트 감지 | UI에 2초 이내 표시 |
| 클립 편집 | trim 조작 후 미리보기 | 원본/9:16 동기화 |
| 내보내기 | 3개 클립 동시 | 진행률 + 완료 알림 |
| 반응형 | 1280x720 ~ 2560x1440 | 레이아웃 정상 |

---

## 8. Team & Responsibilities

| 담당자 | 역할 | 산출물 |
|--------|------|--------|
| Jemin | Web UI 디자인 + 프론트엔드 구현 | `DESIGN.md`, Web UI |
| Seongheum | 라이브 스트리밍 캡처 + 실시간 파이프라인 | `LIVE_SERVER.md`, Stream Server |
| Sungman | Transcription + 하이라이트 감지 + 클립 편집 | `Transcript.md`, Detection Engine |

## 9. Tech Stack Summary

| 레이어 | 기술 |
|--------|------|
| Language | Python ≥ 3.10 |
| Web Server | FastAPI 또는 Flask |
| Realtime | WebSocket |
| Stream Capture | OBS RTMP (prod) / yt-dlp (demo) |
| Audio Processing | ffmpeg, Silero VAD |
| STT | Deepgram Nova-3 (prod) / faster-whisper (dev) |
| OCR | EasyOCR / Tesseract (Valorant 킬피드) |
| Video Editing | ffmpeg |
| Frontend | HTML/CSS/JS or React, Dark mode only |

## 10. Key Milestones

| 일정 | 내용 |
|------|------|
| 2026-03-28 11:30 AM | 전체 문서 리뷰 및 테스트 코드 작성 방향 논의 |

## 11. Resolved Decisions

이전 Open Questions에서 결정된 사항들:

| 질문 | 결정 |
|------|------|
| YouTube API로 캡처 가능한가? | ❌ ToS 위반. OBS RTMP 수신으로 전환. yt-dlp는 demo only. |
| 하이라이트 감지 기준? | 복합 (오디오 0.3 + 키워드 0.3 + 킬피드 OCR 0.4) |
| 크롭 전략? | 정적 중앙 크롭 (MVP). Valorant 크로스헤어가 중앙이므로 적합. |
| 실시간 vs 일괄? | **실시간 처리 우선** |
| 지원 게임 범위? | **Valorant만** |
| 언어? | **영어만** |
| UI 구현 방식? | **Web View** (Python 서버) |
| 다크/라이트? | **다크 모드 전용** |
| 게임 성능 영향? | **고려하지 않음** |

## 12. Remaining Open Issues

- OBS → 본 시스템 동시 송출 시 OBS 설정 가이드 필요 (Custom RTMP server 추가)
- Valorant 킬피드 OCR ROI 좌표는 게임 해상도(1080p/1440p)별로 사전 정의 필요
- 하이라이트 threshold(0.6) 값은 실제 Valorant 테스트 후 튜닝
- Web UI 프레임워크 최종 선정 (vanilla JS vs React)
- Deepgram API 키 관리 및 비용 상한 설정
