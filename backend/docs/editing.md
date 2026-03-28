# editing.md — 클립 편집 모듈 설계

**담당:** Sungman
**상위 문서:** [backend.md](backend.md)

---

## 1. 목표

하이라이트 감지 결과를 기반으로 16:9 원본 영상을 9:16 vertical video로 자동 편집한다. 줌/슬로모션 이펙트와 2가지 템플릿 시스템을 지원한다.

## 2. 교전 이펙트 (Zoom & Slow-Motion)

교전(킬피드 감지) 시점에 자동으로 줌 + 슬로모션을 적용하여 하이라이트 임팩트를 극대화한다.

| 이펙트 | 값 | 적용 시점 |
|--------|-----|-----------|
| **Zoom** | 1.2x ~ 1.5x (중앙 기준) | 킬 발생 직전 0.3초 ~ 킬 후 1초 |
| **Slow-Motion** | 0.5x ~ 0.7x 속도 | 킬 발생 직전 0.5초 ~ 킬 후 0.5초 |
| **Zoom 복귀** | ease-out 전환 (0.3초) | 슬로모션 종료 후 원래 배율로 복귀 |

- 연속 킬(더블킬, 트리플킬 등) 시 줌/슬로모션 구간이 자연스럽게 이어짐
- 줌 중심점: 크로스헤어 위치 (Valorant 기본 화면 중앙)

## 3. 숏폼 템플릿 시스템

### 템플릿 A: 오버레이 구성 (Overlay Layout)

```
┌─────────────────────┐
│  [Kill Log]  (opt)  │  ← 상단: 킬 로그 오버레이 (선택)
│                     │
│   게임 화면 (9:16)  │  ← 중앙: 16:9 → 9:16 중앙 크롭 (전체 화면)
│   줌/슬로모션 적용   │
│                     │
│ ┌─────────────────┐ │
│ │ 스트리머 얼굴    │ │  ← 하단: 웹캠 피드 (항상 표시)
│ └─────────────────┘ │
└─────────────────────┘
```

- 게임 화면이 세로 전체를 차지
- 스트리머 얼굴: 하단 고정, 반투명 배경 또는 원형/라운드 마스크
- 킬 로그: 상단 오버레이, 킬 발생 시 표시 (optional toggle)

### 템플릿 B: 동적 구성 (Dynamic Layout)

- 게임 화면이 세로 전체를 차지 (방해 요소 최소화)
- 스트리머 얼굴: **VAD 발화 감지** 시에만 하단에 2~3초 등장 후 fade-out
- 킬 로그: 킬피드 감지 시에만 상단에 2~3초 등장 후 fade-out

| 요소 | 트리거 | 표시 시간 | 전환 효과 |
|------|--------|-----------|-----------|
| 스트리머 얼굴 | VAD 음성 감지 또는 표정 변화 | 2~3초 | slide-up + fade-out |
| 킬 로그 | KillFeedDetector 이벤트 | 2~3초 | slide-down + fade-out |

> **표정 변화 감지 (Optional, MVP 제외):** MVP에서는 VAD 기반 발화 감지만으로 얼굴 표시를 트리거한다.

## 4. 기본 클리핑 규칙

- 하이라이트 시점 **5초 전**부터 시작
- 최소 15초, 최대 30초
- 파일명: `highlight_{timestamp}_{score}_{template}.mp4`

## 5. 클리핑 로직

```python
class ClipEditor:
    MIN_DURATION = 15.0
    MAX_DURATION = 30.0
    PRE_BUFFER = 5.0

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

## 6. 출력 규격

| 항목 | 값 |
|------|-----|
| 해상도 | 1080x1920 |
| 비율 | 9:16 |
| 코덱 | H.264 (video), AAC (audio) |
| 길이 | 15~30초 |
| 포맷 | .mp4 |
| 파일명 | `highlight_{timestamp}_{score}_{template}.mp4` |

## 7. 의존성

- **ffmpeg** ≥ 6.0
- **Python** ≥ 3.10

## 8. 테스트 계획

| 테스트 항목 | 방법 | 성공 기준 |
|-------------|------|-----------|
| 9:16 크롭 | 크로스헤어 위치 확인 | 중앙 30% 이내 |
| 클립 길이 | 전체 생성 클립 | 15~30초 범위 100% |
| 줌/슬로모션 | 킬 발생 시점 전후 이펙트 | 줌 1.2~1.5x, 속도 0.5~0.7x |
| 템플릿 A | 오버레이 레이아웃 | 웹캠 하단 고정, 킬 로그 상단 |
| 템플릿 B | VAD 발화 시 얼굴 팝업, 킬 시 로그 팝업 | 2~3초 표시 후 fade-out |
