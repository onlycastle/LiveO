# Transcript.md — Transcription + 하이라이트 감지 및 편집 모듈 설계

**담당:** Sungman
**상위 문서:** PRD.md

---

## 1. 목표

라이브 스트리밍 오디오를 **실시간**으로 영어 텍스트 변환(STT)하고, 멀티시그널 기반으로 **Valorant** 하이라이트 구간을 자동 감지하여 15~30초 길이의 vertical video(9:16) 클립으로 편집한다.

## 2. Scope

- **게임:** Valorant만 고려
- **언어:** 영어만 지원
- **처리 방식:** 실시간 처리 우선

## 3. 모듈 구성

1. **Transcription** — 오디오 → 영어 텍스트 (실시간)
2. **Highlight Detection** — 멀티시그널 하이라이트 감지
3. **Video Editing** — 16:9 → 9:16 변환 + 클리핑

---

## Part A: Transcription

### A.1 STT 엔진 비교 (영어 기준)

| 엔진 | 지연 시간 | 비용 | 비고 |
|------|-----------|------|------|
| **Deepgram Nova-3** | <300ms | $0.46/hr | **추천: 최저 지연** |
| Google Cloud STT | <500ms | $0.006~0.024/15s | 문서 풍부 |
| WhisperKit (로컬) | ~460ms | 무료 | GPU 필요, **비용 최적** |
| faster-whisper (로컬) | ~500ms+ | 무료 | CPU 가능 |

### A.2 실시간 파이프라인

```
Audio Pipe (from LIVE_SERVER, PCM 16kHz)
       │
       ▼
  Silero VAD (<1ms) ── 음성 구간만 통과
       │
       ▼
  Deepgram Streaming API (<300ms)  [prod]
  faster-whisper                    [dev]
       │
       ▼
  TranscriptSegment (영어 텍스트)
```

### A.3 Silero VAD

게임 오디오에서 스트리머 음성 구간만 선별:

- 정확도: 87.7% TPR at 5% FPR
- 처리 속도: 30ms 청크당 <1ms
- 모델 크기: 1.8MB

```python
import torch

model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad')
(get_speech_timestamps, _, read_audio, _, _) = utils

audio = read_audio('audio_chunk.wav')
speech_timestamps = get_speech_timestamps(audio, model)
```

### A.4 오디오 소스 분리 (Optional, MVP 제외)

Demucs로 보컬 분리 가능 (100~500ms 추가 지연). STT 정확도 이슈 발생 시 적용.

### A.5 출력 데이터 규격

```python
@dataclass
class TranscriptSegment:
    text: str              # 인식된 영어 텍스트
    start_time: float      # 스트림 기준 시작 시간 (초)
    end_time: float
    confidence: float      # 0.0 ~ 1.0
    language: str = "en"   # 영어 고정
    is_speech: bool = True
```

---

## Part B: Highlight Detection

### B.1 멀티시그널 감지 (Valorant 특화)

| 신호 | 가중치 | 감지 방법 | 지연 |
|------|--------|-----------|------|
| **오디오 흥분도** | 0.3 | 음량 급증 + 피치 변화 (EMA 기반) | <100ms |
| **키워드 매칭** | 0.3 | Transcript에서 영어 감탄사/게임 용어 | STT 지연 종속 |
| **킬피드 OCR** | 0.4 | Valorant 킬피드 영역 (우상단) 텍스트 변화 | ~200ms |

### B.2 오디오 기반 감지

```python
import numpy as np

class AudioExcitementDetector:
    def __init__(self, volume_threshold: float = 0.7):
        self.baseline_volume = 0.0

    def detect(self, audio_chunk: np.ndarray, sample_rate: int) -> float:
        """0.0~1.0 흥분도 점수 반환"""
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        if self.baseline_volume > 0:
            spike_ratio = rms / self.baseline_volume
        else:
            spike_ratio = 0.0
        self.baseline_volume = 0.95 * self.baseline_volume + 0.05 * rms
        return min(spike_ratio / 3.0, 1.0)
```

### B.3 키워드 기반 감지 (영어)

```python
HIGHLIGHT_KEYWORDS = [
    "oh my god", "insane", "clutch", "ace", "headshot",
    "let's go", "no way", "what", "nice", "one tap",
    "flawless", "thrifty", "team ace", "collateral",
    "oh", "wow", "dude", "bro", "crazy"
]

class KeywordDetector:
    def detect(self, transcript: TranscriptSegment) -> float:
        text_lower = transcript.text.lower()
        matches = sum(1 for kw in HIGHLIGHT_KEYWORDS if kw in text_lower)
        return min(matches / 3.0, 1.0)
```

### B.4 Valorant 킬피드 OCR

Valorant 킬피드는 화면 우상단에 고정 위치로 표시된다.

```python
class ValorantKillFeedDetector:
    # Valorant 1920x1080 기준 킬피드 ROI
    KILLFEED_ROI = {
        "1080p": (1450, 40, 450, 280),  # (x, y, w, h)
        "1440p": (1940, 50, 600, 370),
    }

    def __init__(self, resolution: str = "1080p"):
        self.region = self.KILLFEED_ROI[resolution]
        self.prev_text = ""

    def detect(self, frame: np.ndarray) -> float:
        x, y, w, h = self.region
        roi = frame[y:y+h, x:x+w]
        text = self._ocr(roi)  # EasyOCR / Tesseract
        if text != self.prev_text and len(text) > len(self.prev_text):
            self.prev_text = text
            return 1.0
        self.prev_text = text
        return 0.0
```

### B.5 하이라이트 판정

```python
@dataclass
class HighlightCandidate:
    timestamp: float
    score: float
    audio_score: float
    keyword_score: float
    killfeed_score: float
    duration: float = 20.0

class HighlightAggregator:
    THRESHOLD = 0.6

    def aggregate(self, audio: float, keyword: float, killfeed: float,
                  timestamp: float) -> HighlightCandidate | None:
        score = (audio * 0.3) + (keyword * 0.3) + (killfeed * 0.4)
        if score >= self.THRESHOLD:
            return HighlightCandidate(
                timestamp=timestamp, score=score,
                audio_score=audio, keyword_score=keyword,
                killfeed_score=killfeed,
            )
        return None
```

---

## Part C: Video Editing (16:9 → 9:16)

### C.1 MVP: FFmpeg 정적 중앙 크롭

Valorant은 크로스헤어가 화면 중앙에 있으므로 중앙 크롭이 핵심 액션을 잘 담는다.

```bash
ffmpeg -i source.ts \
  -ss {start} -t {duration} \
  -vf "crop=608:1080:656:0,scale=1080:1920" \
  -c:v libx264 -crf 20 -preset medium \
  -c:a aac -b:a 128k \
  highlight_{timestamp}_{score}.mp4
```

### C.2 클리핑 로직

```python
class ClipEditor:
    MIN_DURATION = 15.0
    MAX_DURATION = 30.0
    PRE_BUFFER = 5.0  # 하이라이트 5초 전부터

    def create_clip(self, highlight: HighlightCandidate,
                    source_path: str, output_path: str) -> None:
        start = max(0, highlight.timestamp - self.PRE_BUFFER)
        duration = min(self.MAX_DURATION,
                       max(self.MIN_DURATION, highlight.duration))
        cmd = [
            "ffmpeg", "-i", source_path,
            "-ss", str(start), "-t", str(duration),
            "-vf", "crop=608:1080:656:0,scale=1080:1920",
            "-c:v", "libx264", "-crf", "20", "-preset", "medium",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]
        subprocess.run(cmd, check=True)
```

### C.3 출력 규격

| 항목 | 값 |
|------|-----|
| 해상도 | 1080x1920 |
| 비율 | 9:16 |
| 코덱 | H.264 (video), AAC (audio) |
| 길이 | 15~30초 |
| 포맷 | .mp4 |
| 파일명 | `highlight_{timestamp}_{score}.mp4` |

---

## 4. 의존성

- **Deepgram SDK** 또는 **faster-whisper** ≥ 1.0
- **Silero VAD** (torch hub)
- **ffmpeg** ≥ 6.0
- **EasyOCR** 또는 **Tesseract** (Valorant 킬피드 OCR)
- **Python** ≥ 3.10, **numpy**, **torch**

## 5. 테스트 계획

| 테스트 항목 | 방법 | 성공 기준 |
|-------------|------|-----------|
| STT 정확도 | 영어 Valorant 스트리밍 5분 | WER < 20% |
| VAD 정확도 | 게임 오디오 혼합 샘플 | TPR > 85% |
| 킬피드 OCR | Valorant 킬피드 스크린샷 50장 | 감지율 > 80% |
| 하이라이트 감지 | 수동 레이블 20개 vs 자동 | recall > 70%, precision > 60% |
| 9:16 크롭 | 크로스헤어 위치 확인 | 중앙 30% 이내 |
| 클립 길이 | 전체 생성 클립 | 15~30초 범위 100% |

## 6. Open Issues

- Valorant 킬피드 ROI 좌표는 1080p/1440p 해상도별 사전 정의 → 실측 필요
- 하이라이트 threshold(0.6) 값은 실제 Valorant 영상으로 튜닝
- Deepgram 비용 상한 설정 필요
