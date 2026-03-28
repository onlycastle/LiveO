# Shorts Factory — Indicator System Specification

## Overview

인디케이터는 유튜브 게임 라이브 스트리밍을 실시간으로 분석하여 **쇼츠로 제작할 가치가 있는 구간**을 자동으로 감지하는 핵심 시스템이다. 각 인디케이터는 독립적으로 동작하며, 복수의 인디케이터가 동시에 활성화될 때 **confidence score**가 높아져 쇼츠 후보로 추천된다.

---

## Indicator Architecture

```
YouTube Live Stream
    │
    ├── Video Feed ──────────► [Game Highlight] [Kill/Death Event]
    │                          [Stream Overlay Alert]
    │
    ├── Audio Feed ──────────► [Audio Spike] [Transcription Keyword]
    │
    ├── Chat Feed ───────────► [Chat Velocity] [Emote Flood]
    │   (YouTube Live Chat API)  [Chat Sentiment Shift] [Super Chat Surge]
    │                            [Membership Gift Wave] [Poll/Prediction Moment]
    │
    ├── Viewer Metrics ──────► [Viewer Count Spike] [Clip Creation Burst]
    │   (YouTube Analytics API)
    │
    └── User Input ──────────► [Manual Capture]
```

---

## Indicators — Detailed Specification

### 1. Manual Capture (수동 캡처)

| Property | Value |
|----------|-------|
| **Type ID** | `manual` |
| **Input Source** | User interaction (button hold) |
| **Detection Method** | UI 버튼을 1.5초 이상 홀드하면 해당 시점을 하이라이트로 마킹 |
| **Latency** | 즉시 (0ms) |
| **Confidence Weight** | 1.0 (사용자 직접 지정이므로 최고 가중치) |

**근거**: 스트리머 본인이나 편집자가 직접 "이 순간이 쇼츠감"이라고 판단하는 가장 정확한 신호. 알고리즘이 놓칠 수 있는 맥락적 판단을 보완한다.

**구현 방향**:
- 버튼 홀드 시작/종료 타임스탬프 기록
- 홀드 중에는 전후 15초 버퍼를 자동 포함
- 홀드 길이에 따라 구간 확장 가능 (1.5s = 30s 쇼츠, 3s = 45s 쇼츠)

---

### 2. Chat Velocity (채팅 속도 급증)

| Property | Value |
|----------|-------|
| **Type ID** | `chat_velocity` |
| **Input Source** | YouTube Live Chat API (`liveChatMessages`) |
| **Detection Method** | 슬라이딩 윈도우 기반 채팅 속도 모니터링 (messages/sec) |
| **Threshold** | 최근 5분 평균 대비 3x 이상 급증 시 활성화 |
| **Latency** | ~2초 (API polling interval) |
| **Confidence Weight** | 0.7 |

**근거**: 채팅 속도 급증은 시청자 집단 반응의 가장 보편적인 신호. 게임의 결정적 순간, 스트리머의 재미있는 발언, 예상치 못한 이벤트 등 다양한 하이라이트에 반응한다. Twitch/YouTube 클리핑 데이터 분석에서 상위 클립의 87%가 채팅 속도 급증 구간과 겹친다는 연구 결과가 있다.

**구현 방향**:
```typescript
interface ChatVelocityConfig {
  windowSize: 10;         // 10초 슬라이딩 윈도우
  baselineWindow: 300;    // 5분 기준선
  threshold: 3.0;         // 기준선 대비 배수
  cooldown: 15;           // 활성화 후 15초 쿨다운
  pollInterval: 2000;     // YouTube API polling (ms)
}
```
- YouTube Live Chat API에서 `liveChatMessages.list()` 호출
- `nextPageToken` + `pollingIntervalMillis` 활용
- 초당 메시지 수를 슬라이딩 윈도우로 계산
- 기준선(5분 이동 평균) 대비 급증 비율로 intensity 계산

---

### 3. Super Chat Surge (슈퍼챗 집중)

| Property | Value |
|----------|-------|
| **Type ID** | `superchat` |
| **Input Source** | YouTube Live Chat API (`superChatEvent`, `superStickerEvent`) |
| **Detection Method** | 단위 시간당 슈퍼챗 건수 및 금액 모니터링 |
| **Threshold** | 30초 내 3건 이상 또는 누적 금액 ₩50,000 이상 |
| **Latency** | ~2초 |
| **Confidence Weight** | 0.6 |

**근거**: 슈퍼챗은 시청자가 **유료로** 반응하는 행위이므로, 단순 채팅보다 강한 감정적 반응을 나타낸다. 특히 연속 슈퍼챗은 "이 순간은 돈을 낼 만큼 가치 있다"는 집단 신호다.

**구현 방향**:
```typescript
interface SuperChatConfig {
  countThreshold: 3;      // 30초 내 3건
  amountThreshold: 50000; // 누적 ₩50,000
  windowSize: 30;         // 30초 윈도우
  cooldown: 20;
}
```
- `liveChatMessages` 응답의 `snippet.type === 'superChatEvent'` 필터
- 금액은 `snippet.superChatDetails.amountMicros` / 1,000,000
- 건수와 금액 두 조건 OR 로직

---

### 4. Audio Spike (오디오 볼륨 급증)

| Property | Value |
|----------|-------|
| **Type ID** | `audio_spike` |
| **Input Source** | Stream audio via Web Audio API |
| **Detection Method** | RMS 볼륨 레벨의 급격한 상승 감지 |
| **Threshold** | 최근 30초 평균 대비 2.5x 이상 |
| **Latency** | ~100ms (실시간) |
| **Confidence Weight** | 0.8 |

**근거**: 스트리머가 소리를 지르거나, 흥분하거나, 환호하는 순간은 거의 항상 하이라이트와 일치한다. 오디오는 게임의 결정적 순간(폭발, 킬 사운드 등)과 스트리머의 감정 반응을 동시에 캡처한다. 영상 분석보다 훨씬 가볍고 빠르면서도 정확도가 높다.

**구현 방향**:
```typescript
interface AudioSpikeConfig {
  analyserFftSize: 2048;
  rmsBaselineWindow: 30;  // 30초 기준선
  spikeMultiplier: 2.5;
  sustainDuration: 500;   // 500ms 이상 지속 시 활성화
  cooldown: 10;
}
```
- YouTube iframe에서 직접 오디오 추출 불가 → **별도 오디오 스트림** 또는 **OBS WebSocket** 연동 필요
- 대안: 브라우저 `getDisplayMedia()` + Web Audio API로 시스템 오디오 캡처
- `AnalyserNode.getByteTimeDomainData()` → RMS 계산
- 급격한 변화량(delta)과 절대 레벨 모두 고려

---

### 5. Emote Flood (이모트 스팸)

| Property | Value |
|----------|-------|
| **Type ID** | `emote_flood` |
| **Input Source** | YouTube Live Chat API |
| **Detection Method** | 동일/유사 이모지가 단시간에 대량 반복 |
| **Threshold** | 10초 내 같은 이모지 15회 이상 |
| **Latency** | ~2초 |
| **Confidence Weight** | 0.65 |

**근거**: 이모트 스팸은 채팅 속도보다 **더 구체적인** 감정 신호다. 시청자들이 단순히 대화하는 게 아니라, 같은 반응을 집단적으로 표현하는 것이다. 특히 게임 스트리밍에서 "😂" 스팸은 재밌는 장면, "💀" 스팸은 충격적인 장면, "🔥" 스팸은 멋진 플레이를 의미한다.

**구현 방향**:
```typescript
interface EmoteFloodConfig {
  windowSize: 10;          // 10초 윈도우
  sameEmoteThreshold: 15;  // 같은 이모지 15회
  anyEmoteThreshold: 30;   // 아무 이모지 30회
  cooldown: 10;
  trackedEmotes: ['😂', '💀', '🔥', '😱', '🤯', '❤️', 'GG', 'gg'];
}
```
- 채팅 메시지에서 이모지/이모트 추출 (Unicode emoji regex)
- 이모지별 카운터를 슬라이딩 윈도우로 관리
- YouTube 커스텀 이모지는 `:emojiName:` 패턴으로 파싱

---

### 6. Chat Sentiment Shift (채팅 감정 변화)

| Property | Value |
|----------|-------|
| **Type ID** | `sentiment_shift` |
| **Input Source** | YouTube Live Chat API + NLP Model |
| **Detection Method** | 채팅 감정 분석 (흥분/충격/슬픔/분노) 급변 감지 |
| **Threshold** | 감정 점수 delta > 0.4 (5초 윈도우) |
| **Latency** | ~3초 (모델 추론 포함) |
| **Confidence Weight** | 0.75 |

**근거**: 단순 채팅 속도(양)가 아닌 **감정의 질적 변화**를 감지한다. 예를 들어 평화로운 파밍 중 갑자기 "미쳤다!!!" "실화냐" 같은 흥분 반응이 쏟아지면, 채팅 속도는 아직 급증하지 않았더라도 하이라이트가 발생했다는 신호다. Chat Velocity와 결합하면 정밀도가 크게 향상된다.

**구현 방향**:
```typescript
interface SentimentConfig {
  model: 'distilbert-base-multilingual-cased';  // 경량 다국어 모델
  batchSize: 20;           // 20개 메시지 단위 배치 분석
  windowSize: 5;           // 5초 윈도우
  deltaThreshold: 0.4;     // 감정 변화량 임계값
  emotions: ['excitement', 'shock', 'joy', 'frustration', 'neutral'];
  cooldown: 15;
}
```
- 채팅 메시지를 배치로 모아 감정 분류
- 온디바이스 추론 (ONNX Runtime 또는 TF.js) 또는 서버사이드 API
- 감정 분포의 시간 변화를 추적하여 급격한 shift 감지

---

### 7. Viewer Count Spike (시청자 수 급증)

| Property | Value |
|----------|-------|
| **Type ID** | `viewer_spike` |
| **Input Source** | YouTube Data API v3 (`videos.list`, `liveStreamingDetails`) |
| **Detection Method** | 동시 시청자 수 급증 감지 |
| **Threshold** | 최근 10분 평균 대비 1.5x 이상 |
| **Latency** | ~30초 (API rate limit) |
| **Confidence Weight** | 0.5 |

**근거**: 시청자 수 급증은 외부 공유(트위터, 디스코드)나 레이드/호스팅의 결과다. 이 시점 **직전**에 바이럴할 만한 장면이 있었거나, 급증 시점에서 스트리머가 특별한 퍼포먼스를 보이는 경우가 많다. 단독으로는 약한 신호이지만, 다른 인디케이터와 결합하면 "이 클립이 바이럴됐다"는 사후 확인 역할을 한다.

**구현 방향**:
```typescript
interface ViewerSpikeConfig {
  pollInterval: 30000;     // 30초마다 API 호출
  baselineWindow: 600;     // 10분 기준선
  spikeMultiplier: 1.5;
  cooldown: 60;            // 1분 쿨다운 (변화가 느린 지표)
}
```
- `videos.list(part='liveStreamingDetails')` → `concurrentViewers`
- API quota 효율을 위해 polling 간격 30초
- 급증 감지 시 해당 시점 전후 2분을 하이라이트 후보로 마킹

---

### 8. Clip Creation Burst (클립 생성 폭발)

| Property | Value |
|----------|-------|
| **Type ID** | `clip_burst` |
| **Input Source** | YouTube Clips (간접 감지 — Chat 메시지 패턴) |
| **Detection Method** | 시청자들이 클립을 만드는 행위의 간접 신호 감지 |
| **Threshold** | 채팅에서 "클립", "clip", "ㅋㅋㅋ 저장" 등 키워드 3회 이상 / 30초 |
| **Latency** | ~3초 |
| **Confidence Weight** | 0.85 |

**근거**: 시청자가 직접 클립을 만드는 행위 자체가 "이 순간은 쇼츠감"이라는 가장 직접적인 증거다. YouTube Clips API가 실시간 접근을 제공하지 않으므로, 채팅에서의 간접 신호(클립 관련 키워드)를 감지한다. 이 신호의 정밀도가 매우 높아 confidence weight를 높게 설정한다.

**구현 방향**:
```typescript
interface ClipBurstConfig {
  keywords: ['클립', 'clip', 'clipped', '저장', '짤', '캡처', 'saved'];
  windowSize: 30;
  threshold: 3;
  cooldown: 20;
}
```
- 채팅 메시지에서 클립 관련 키워드 regex 매칭
- 한국어/영어 혼용 지원

---

### 9. Kill/Death Event (게임 킬/데스 이벤트)

| Property | Value |
|----------|-------|
| **Type ID** | `kill_event` |
| **Input Source** | Video feed (OCR/Game API) |
| **Detection Method** | 게임 화면의 킬피드/킬 카운터 OCR 또는 게임별 API 연동 |
| **Threshold** | 멀티킬(3+) 또는 에이스 감지 |
| **Latency** | ~1초 (OCR) / 즉시 (Game API) |
| **Confidence Weight** | 0.9 |

**근거**: FPS/배틀로얄 게임에서 킬 이벤트는 가장 객관적인 하이라이트 지표다. 특히 멀티킬, 에이스, 클러치는 쇼츠 조회수가 가장 높은 콘텐츠 유형이다. 게임 화면의 킬피드는 위치가 고정되어 있어 OCR 정확도가 높다.

**구현 방향**:
```typescript
interface KillEventConfig {
  detectionMethod: 'ocr' | 'game_api';
  // OCR 설정
  killfeedRegion: { x: 0.65, y: 0.05, w: 0.35, h: 0.3 };  // 화면 우상단
  ocrInterval: 500;        // 500ms 마다 OCR
  multiKillThreshold: 3;   // 3킬 이상
  // Game API 설정 (게임별)
  supportedGames: ['valorant', 'lol', 'overwatch', 'pubg', 'fortnite'];
  cooldown: 5;
}
```
- **OCR 방식**: 킬피드 영역 크롭 → Tesseract.js 또는 경량 모델로 텍스트 인식
- **Game API 방식**: Valorant Tracker API, Riot API 등 게임별 연동
- **Valorant 특화**: 킬피드 위치 고정 (우상단), 에이스/클러치 판별 패턴
- 게임 종류 자동 감지 (화면 레이아웃 분석 또는 스트림 제목 파싱)

---

### 10. Transcription Keyword (전사 키워드 감지)

| Property | Value |
|----------|-------|
| **Type ID** | `keyword` |
| **Input Source** | Real-time speech-to-text (Whisper / Web Speech API) |
| **Detection Method** | 스트리머 음성 전사에서 감탄/흥분 키워드 감지 |
| **Threshold** | 10초 내 키워드 2회 이상 |
| **Latency** | ~2초 (STT 지연) |
| **Confidence Weight** | 0.7 |

**근거**: 스트리머가 말하는 내용은 하이라이트의 가장 즉각적인 신호다. "미쳤다", "OMG", "GG" 같은 감탄사는 스트리머 본인이 중요한 순간을 인지하고 있다는 증거다. Audio Spike(볼륨)와 달리, 의미적 맥락을 포착한다.

**구현 방향**:
```typescript
interface KeywordConfig {
  sttModel: 'whisper-large-v3';  // 또는 Web Speech API (경량 대안)
  keywords: {
    excitement: ['미쳤다', '미쳤어', 'OMG', 'oh my god', '대박', '실화', '역대급', '레전드'],
    frustration: ['아씨', '에이', '아놔', '존나'],
    victory: ['GG', '이겼다', '승리', '치킨', '에이스', '클러치'],
    surprise: ['뭐야', '헐', '와', '오오오', '세상에'],
  };
  windowSize: 10;
  threshold: 2;
  cooldown: 10;
}
```
- Whisper large-v3로 실시간 전사 (서버사이드) 또는 WebRTC + Deepgram
- 키워드 카테고리별 가중치 부여 (excitement > surprise > victory)
- 연속 키워드 감지 시 intensity 상승

---

### 11. Membership Gift Wave (멤버십 선물 연쇄)

| Property | Value |
|----------|-------|
| **Type ID** | `gift_wave` |
| **Input Source** | YouTube Live Chat API (`membershipGiftingEvent`) |
| **Detection Method** | 멤버십 선물 이벤트 연쇄 감지 |
| **Threshold** | 1분 내 멤버십 선물 3건 이상 |
| **Latency** | ~2초 |
| **Confidence Weight** | 0.55 |

**근거**: 슈퍼챗과 유사하지만 다른 축의 반응이다. 멤버십 선물은 보통 스트리머의 감동적인 순간, 마일스톤 달성, 또는 특별한 이벤트에서 발생한다. 슈퍼챗이 "이 순간이 멋져서"라면, 멤버십 선물은 "이 스트리머를 응원하고 싶어서"라는 더 깊은 감정적 반응이다.

**구현 방향**:
```typescript
interface GiftWaveConfig {
  windowSize: 60;          // 1분 윈도우
  threshold: 3;
  cooldown: 30;
}
```
- `liveChatMessages` 중 `snippet.type === 'membershipGiftingEvent'` 필터

---

### 12. Poll/Prediction Moment (투표/예측 이벤트)

| Property | Value |
|----------|-------|
| **Type ID** | `poll_moment` |
| **Input Source** | YouTube Live Chat API |
| **Detection Method** | 투표/예측 관련 이벤트 및 채팅 패턴 감지 |
| **Threshold** | 투표 생성 또는 결과 발표 시점 |
| **Latency** | ~2초 |
| **Confidence Weight** | 0.6 |

**근거**: 투표/예측이 활성화된 구간은 **긴장감이 최고조**에 달한 순간이다. "이길까 질까", "이번 라운드 어떻게 될까" 같은 불확실성은 쇼츠의 도입부로 최적이다. 특히 예측 결과가 의외일 때 반응이 폭발하므로, 결과 발표 시점 전후가 핵심 구간이다.

**구현 방향**:
```typescript
interface PollConfig {
  chatKeywords: ['투표', 'poll', '예측', 'prediction', '찬성', '반대'];
  // YouTube에서 직접 poll API 접근이 제한적이므로 채팅 패턴으로 간접 감지
  windowSize: 30;
  threshold: 5;            // 투표 관련 채팅 5개 이상
  cooldown: 60;
}
```

---

### 13. Stream Overlay Alert (스트림 오버레이 알림)

| Property | Value |
|----------|-------|
| **Type ID** | `overlay_alert` |
| **Input Source** | Video feed (image detection) 또는 OBS WebSocket |
| **Detection Method** | 팔로우/구독/도네이션 알림 오버레이 감지 |
| **Threshold** | 10초 내 오버레이 알림 3회 이상 |
| **Latency** | ~1초 |
| **Confidence Weight** | 0.5 |

**근거**: 팔로우/구독 알림 폭발은 바이럴 순간과 높은 상관관계를 가진다. 시청자가 방금 본 장면에 감명받아 구독/팔로우를 누르는 행위이므로, 알림 직전 구간이 하이라이트일 확률이 높다.

**구현 방향**:
```typescript
interface OverlayAlertConfig {
  detectionMethod: 'obs_websocket' | 'image_detection';
  // OBS WebSocket: StreamElements/Streamlabs 알림 이벤트 직접 수신
  obsWebsocketUrl: 'ws://localhost:4455';
  // Image Detection: 알림 영역 고정 위치에서 변화 감지
  alertRegion: { x: 0.3, y: 0.0, w: 0.4, h: 0.15 };
  windowSize: 10;
  threshold: 3;
  cooldown: 15;
}
```

---

## Confidence Score Calculation

쇼츠 후보의 최종 confidence score는 동시 활성 인디케이터들의 가중합으로 계산된다:

```typescript
function calculateConfidence(activeIndicators: Indicator[]): number {
  // 개별 가중치 합산
  const weightedSum = activeIndicators.reduce(
    (sum, ind) => sum + ind.confidenceWeight * ind.intensity,
    0
  );

  // 동시 활성 보너스 (2개 이상 동시 활성 시 시너지)
  const synergyBonus = activeIndicators.length >= 2
    ? 0.1 * (activeIndicators.length - 1)
    : 0;

  // 특정 조합 보너스
  const comboBonus = getComboBonus(activeIndicators);

  // 최종 점수 (0-100 스케일)
  return Math.min(100, (weightedSum + synergyBonus + comboBonus) * 100);
}

// 시너지 조합 예시
const COMBO_BONUSES = {
  'kill_event+audio_spike': 0.15,      // 킬 + 소리지름 = 확실한 하이라이트
  'chat_velocity+emote_flood': 0.1,    // 채팅 폭발 + 이모트 스팸 = 집단 반응
  'superchat+sentiment_shift': 0.1,    // 슈퍼챗 + 감정 변화 = 감동 장면
  'audio_spike+keyword': 0.12,         // 볼륨 급증 + 감탄 키워드 = 흥분 피크
};
```

---

## Indicator 우선순위 (Shorts 추천 정렬)

1. **Manual Capture** — 사용자 의도가 가장 우선
2. **Kill Event + Audio Spike** — 게임 하이라이트 확정 (복합)
3. **Chat Velocity + Emote Flood** — 시청자 집단 반응 확정 (복합)
4. **Clip Creation Burst** — 시청자가 직접 인정한 하이라이트
5. **Sentiment Shift + Keyword** — 감정 분석 기반 (복합)
6. **Super Chat Surge** — 유료 반응
7. **Viewer Spike** — 외부 바이럴 신호
8. 기타 단독 인디케이터

---

## Cooldown & Overlap Policy

- 각 인디케이터별 독립 쿨다운 (위 개별 설정 참조)
- 쿨다운 중에도 intensity는 업데이트 (UI 표시용)
- 쇼츠 후보 구간이 겹치면 **병합** (overlap > 50% 시)
- 병합 시 confidence는 더 높은 값 유지, 인디케이터 태그는 합집합

---

## Sensitivity Configuration

사용자가 Settings에서 각 인디케이터의 감도를 0-100으로 조절 가능:

```typescript
interface SensitivityConfig {
  // 0 = 비활성, 50 = 기본, 100 = 최대 민감
  [indicatorType: string]: number;
}

// 감도가 threshold에 영향을 미치는 방식:
// effectiveThreshold = baseThreshold * (1.5 - sensitivity / 100)
// sensitivity 100 → threshold 0.5x (매우 민감)
// sensitivity 50  → threshold 1.0x (기본)
// sensitivity 0   → 비활성
```

---

## Auto-confirm Policy

confidence score가 사용자 설정 임계값(기본 85%) 이상인 후보는 자동으로 confirm 처리되어 쇼츠 생성 파이프라인에 진입한다. 임계값 이하는 사용자 수동 confirm/dismiss 필요.
