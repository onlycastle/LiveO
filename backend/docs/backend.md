# backend.md — 백엔드 서버 설계

**상위 문서:** [PRD.md](../../docs/PRD.md)

---

## 1. 개요

Python 백엔드 서버. 라이브 스트리밍 캡처, 실시간 음성/영상 분석, 하이라이트 감지, 숏폼 클립 편집을 담당한다.

## 2. 역할 분담

| 모듈 | 담당 | 설계 문서 | 설명 |
|------|------|-----------|------|
| **Streaming** | Seongheum | [streaming.md](streaming.md) | 라이브 스트림 캡처 (RTMP / yt-dlp) + 실시간 파이프라인 |
| **Transcript** | Sungman | [transcript.md](transcript.md) | 오디오 → STT + 하이라이트 감지 (멀티시그널) |
| **Editing** | Sungman | [editing.md](editing.md) | 16:9 → 9:16 클립 편집 + 템플릿 시스템 |

## 3. 전체 파이프라인

```
Stream Capture (streaming)
    ├──→ Video segments → RingBuffer → KillFeed OCR (transcript)
    └──→ Audio pipe → VAD → STT → Keyword Detection (transcript)
                     └───→ Audio Excitement Detection (transcript)
                                    │
                                    ▼
                          HighlightAggregator (transcript)
                                    │
                                    ▼
                            ClipEditor (editing)
                                    │
                                    ▼
                          highlight_*.mp4 (9:16)
```

## 4. 기술 스택

| 항목 | 기술 |
|------|------|
| Language | Python ≥ 3.10 |
| Stream Capture | ffmpeg, yt-dlp (demo) |
| Audio | Silero VAD, Deepgram Nova-3 / faster-whisper |
| OCR | EasyOCR / Tesseract |
| Video Editing | ffmpeg |
| API Server | FastAPI (예정) |
| Realtime | WebSocket |

## 5. 디렉토리 구조

```
backend/
├── docs/
│   ├── backend.md       ← 이 문서
│   ├── streaming.md     ← 스트리밍 캡처
│   ├── transcript.md    ← STT + 하이라이트 감지
│   └── editing.md       ← 클립 편집
├── __init__.py
├── __main__.py          ← CLI 엔트리포인트
├── capture.py           ← RTMP / yt-dlp 캡처
├── events.py            ← 이벤트 정의
├── pipeline.py          ← 파이프라인 오케스트레이션
└── ring_buffer.py       ← 영상 순환 저장
```
