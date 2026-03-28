# LiveO Ralph Loop 실행 계획 (v5)

## 0. 목적

이 문서는 LiveO 프로젝트에서 Ralph Loop가 끊김 없이 구현과 검증을 반복할 수 있도록,
실행 순서와 테스트 전략을 결정 완료 상태로 고정한 계획서다.

목표는 다음 핵심 흐름을 완성하고 검증하는 것이다.

`Twitch URL 입력 -> POST /api/stream/start -> 세그먼트 생성 -> 하이라이트 감지 -> 후보 생성 -> 9:16 숏폼 렌더 -> Web UI 확인 -> 파일 다운로드`

이번 개정(v5)의 핵심 변경 5가지:

1. `FakeCapture` + fake generation 전략 추가. test mode에서 ffmpeg/yt-dlp 없이 동작한다.
2. `use-liveo.ts`에 transcript/indicator WS 처리 추가. IndicatorDashboard mock 제거 명시.
3. Template enum을 3개(`blur_fill|letterbox|cam_split`)로 고정. 프론트 기존 타입 유지.
4. STT skip 범위를 `test_transcriber.py` 모델 로드 2건으로 축소. 유효한 회귀 검증 보존.
5. `/artifacts` StaticFiles 마운트 + fake artifact 생성으로 다운로드 E2E 경로 완성.

---

## 1. 현재 상태 스냅샷

### 1.1 이미 있는 것

| 축 | 파일 | 상태 |
|----|------|------|
| 캡처 | `backend/capture.py` | RTMP / yt-dlp 캡처 구현 존재 |
| 파이프라인 | `backend/pipeline.py`, `backend/ring_buffer.py`, `backend/events.py` | 세그먼트 저장 + 이벤트 발행 존재 |
| API 서버 | `backend/server.py` | stream / candidates / generate / settings / ws 엔드포인트 존재 |
| 서버 엔트리 | `backend/__main__.py` | `python -m backend --serve` 가능 |
| STT | `backend/stt.py`, `backend/vad.py`, `backend/transcript.py` | faster-whisper + Silero VAD 구현 존재 (optional dependency) |
| 모델 | `backend/models.py` | Pydantic 스키마 존재 (불완전, 아래 참조) |
| WS 매니저 | `backend/ws_manager.py` | WebSocket 브로드캐스트 관리 존재 |
| 백엔드 테스트 | `tests/test_*.py` (9개) | 기본 테스트 존재 (4개 실패, 아래 참조) |
| 프론트 상태 훅 | `frontend/lib/use-websocket.ts` | WebSocket 수신 로직 존재 (bootstrap GET 없음) |
| 프론트 UI | `frontend/app/page.tsx`, `frontend/components/**` | 랜딩, 대시보드, 후보 카드, 프리뷰 UI 존재 |
| 레퍼런스 샘플 | `resources/samples/*` | 4개 숏폼 샘플, 각 29 프레임, 이미지만 존재 (영상 없음) |

### 1.2 지금 바로 실패하는 것

| 이슈 | 원인 | 파일 |
|------|------|------|
| `npm run build` 실패 | `LeftPanel`의 필수 prop `transcriptLines`를 `page.tsx`에서 전달하지 않음 | `page.tsx:70`, `LeftPanel.tsx:9` |
| `pytest tests -q` 4개 실패 | `test_transcriber.py`, `test_stt.py`가 `faster-whisper`를 직접 import하지만 `[dev]` extras에 미포함 | `pyproject.toml:22`, `stt.py:34` |
| FE/BE 스키마 불일치 | `GeneratedShort`에 `template`, `caption`, `artifactUrl` 필드 없음 | `models.py:70`, `types.ts:51` |
| Template enum 불일치 | FE: `blur_fill`/`letterbox`/`cam_split`, BE: `crop`/`letterbox`/`cam_split`/`overlay`/`dynamic` | `types.ts:49`, `models.py:127` |
| PRD↔BE source 불일치 | PRD는 `yt-dlp`, 백엔드는 `demo`만 허용 | `PRD.md:475`, `models.py:89` |
| 프론트 100% mock 데이터 | `page.tsx`, `GeneratedShortsGrid`, `IndicatorDashboard`가 `mock-data.ts` import | `page.tsx:10`, `GeneratedShortsGrid.tsx:11` |
| StreamEmbed 하드코딩 | `valorant` 채널 iframe 하드코딩, 입력 URL 미사용 | `StreamEmbed.tsx:7` |
| CONFIRM/SKIP/GENERATE 미연결 | 버튼에 onClick 핸들러 없음 (UI만 존재) | `ShortsCandidateCard.tsx:159`, `ShortsPreviewModal.tsx:60` |
| 다운로드 핸들러 없음 | DOWNLOAD 버튼에 onClick 없음 | `GeneratedShortsGrid.tsx:128` |
| 생성 mock | `_run_generation()`이 진행률만 mock, 실제 파일 미생성 | `server.py:248` |
| WS reconnect 단순 | `use-websocket.ts`가 3초 후 재연결하지만 exponential backoff 없음 | `use-websocket.ts:22` |
| 테스트 격리 없음 | `test_server.py`가 전역 상태 초기화 없이 실행 | `server.py:37`, `test_server.py:14` |

### 1.3 존재하지 않는 것 (Ralph가 만들어야 함)

| 축 | 필요한 것 |
|----|----------|
| 테스트 캡처 | `backend/capture.py`에 `FakeCapture` 클래스 추가 |
| artifact 서빙 | `backend/server.py`에 `/artifacts` StaticFiles 마운트 |
| 감지기 | `backend/detectors/` + `backend/highlight_aggregator.py` |
| 실제 렌더 | `backend/clip_editor.py` |
| 상태 관리 훅 | `frontend/lib/use-liveo.ts` (bootstrap GET + WS delta 통합 — transcript/indicator 포함) |
| indicator 실연결 | `IndicatorDashboard.tsx` mock-data import 제거, 훅/props 연결 |
| 테스트 디렉토리 | `tests/api/`, `tests/detectors/`, `tests/video/`, `tests/integration/` |
| 테스트 인프라 | `tests/conftest.py` (공유 fixture), `tests/api/conftest.py` |
| 프론트 테스트 인프라 | Playwright dependency, `frontend/playwright.config.ts`, `frontend/tests/e2e/` |
| 테스트 fixture | 3~5초 짧은 영상 파일 (ffmpeg 생성) |
| data-testid | 프론트엔드 전 컴포넌트에 0개 존재 |
| 프론트 test scripts | `test:fast`, `test:e2e`, `test:visual` in `package.json` |

---

## 2. 비협상 규칙

### 2.1 실행 환경

Python 테스트는 시스템 `python`이나 `pytest` 명령을 믿지 않는다.
항상 프로젝트 venv를 사용한다.

```bash
./.venv/bin/python -m pytest ...
```

프런트 작업 전에는 반드시 의존성을 설치한다.

```bash
cd frontend && npm install
```

### 2.2 API Key 금지

이 프로젝트는 로컬에서 API Key 없이 완전히 동작해야 한다.

- STT: `faster-whisper` (로컬 모델)
- VAD: `Silero VAD` (torch hub, 로컬)
- OCR: `easyocr` (로컬) 또는 `tesseract` (시스템)
- 영상 처리: `ffmpeg` (시스템)

Deepgram, Google Cloud STT 등 클라우드 서비스는 사용하지 않는다.
테스트에서 API Key를 요구하는 import가 있으면 해당 테스트를 skip 처리한다.

### 2.3 Source 문자열 통일

PRD와 백엔드의 source 문자열을 통일한다.

- **정식 값**: `"demo"` (yt-dlp 기반 캡처), `"obs"` (RTMP 기반 캡처)
- PRD의 `"yt-dlp"`는 `"demo"`로 정정한다.
- 프론트엔드에서 Twitch URL 입력 시: `POST /api/stream/start { "source": "demo", "url": "https://twitch.tv/xxx" }`

### 2.4 FakeCapture / Test Mode 캡처 전략

`LIVEO_TEST_MODE=1`일 때 서버는 실제 ffmpeg/yt-dlp 프로세스를 spawn하지 않는다.
대신 `FakeCapture`를 사용하여 캡처 동작을 시뮬레이션한다.

```python
# backend/capture.py에 추가
class FakeCapture(BaseCapture):
    """LIVEO_TEST_MODE=1 전용. 실제 프로세스 없이 캡처 상태만 관리."""

    def __init__(self, url: str = ""):
        self._alive = False
        self.url = url

    def start(self):
        self._alive = True

    def stop(self):
        self._alive = False

    def is_alive(self) -> bool:
        return self._alive

    @property
    def video_stdout(self):
        return None
```

`backend/server.py`의 `stream_start()`에서 분기:

```python
import os

if os.getenv("LIVEO_TEST_MODE") == "1":
    capture = FakeCapture(url=req.url)
    _capture_method = "fake"
elif req.source == "demo":
    capture = YtdlpDemoCapture(req.url)
    _capture_method = "yt-dlp"
else:
    capture = RTMPStreamCapture(req.url)
    _capture_method = "obs-rtmp"
```

FakeCapture 모드에서는:
- Pipeline을 생성하지 않는다 (영상 데이터 없음)
- TranscriptProcessor를 생성하지 않는다
- `_pipeline`은 None으로 유지하되, `is_live` 상태는 `_capture.is_alive()`로 판정한다
- `POST /api/stream/stop` 시 `_capture.stop()` 호출

마찬가지로 `_run_generation()`도 test mode에서는 실제 clip_editor를 호출하지 않고,
빈 artifact 파일을 생성하여 경로만 반환한다:

```python
if os.getenv("LIVEO_TEST_MODE") == "1":
    # 빈 mp4/jpg를 생성하여 다운로드 검증 가능하게 함
    artifact_dir = Path("artifacts/videos")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir = Path("artifacts/thumbs")
    thumb_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_dir / f"{short_id}.mp4"
    thumb_path = thumb_dir / f"{short_id}.jpg"

    # ffmpeg으로 1초짜리 테스트 영상 생성 (1080x1920, 9:16)
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1",
        "-c:v", "libx264", str(artifact_path)
    ], capture_output=True, check=True)

    # 썸네일: 첫 프레임 추출
    subprocess.run([
        "ffmpeg", "-y", "-i", str(artifact_path),
        "-frames:v", "1", str(thumb_path)
    ], capture_output=True, check=True)
else:
    # 실제 clip_editor 호출
    from backend.clip_editor import render
    artifact_path, thumb_path = render(...)
```

### 2.5 테스트 오라클

품질 판정은 하이브리드 전략으로 고정한다.

- `blocking gate`: 결정론적 수치 기준만 사용
- `non-blocking report`: VLM 또는 규칙 기반 주관적 품질 평가 허용

즉 `숏폼다움`, `자극성` 같은 목표를 바로 픽셀 동일성으로 강제하지 않는다.
대신 다음을 정량화해서 게이트로 쓴다.

- 출력 스펙 (해상도, 코덱, 길이)
- 크롭/레이아웃 정합성
- frame continuity
- freeze frame 비율
- motion energy
- cut density
- text occupancy
- overlay dwell time
- first-3s hook 존재 여부

### 2.5 레퍼런스 전략

레퍼런스는 두 계층으로 나눈다.

1. 외부 레퍼런스: `resources/samples/*` — 프레임 이미지 기반 스타일 envelope 계산
2. 내부 골든: Ralph가 deterministic fixture로 직접 생성하고 저장하는 expected outputs

역할은 다음처럼 고정한다.

- 외부 레퍼런스는 `스타일 envelope` 계산용이다. (현재 프레임 이미지만 있으므로 spatial metric만 사용)
- 내부 골든은 `회귀 테스트`용이다.
- 외부 샘플과의 direct pixel match는 금지한다.
- 내부 골든에는 SSIM >= 0.85 허용 오차 기반 비교를 사용한다.

### 2.6 테스트 티어

#### Fast Tier

매 반복마다 실행한다.

- 백엔드 단위 테스트 (STT optional tests 제외)
- API 계약 테스트
- WebSocket 계약 테스트
- 프런트 Playwright `@fast` 태그 테스트
- 프런트 빌드

#### Slow Tier

기능 구현이 연결된 뒤, 또는 일정 체크포인트마다 실행한다.

- 실제 영상 렌더 테스트
- 프레임 비교
- continuity / motion / shortform envelope 테스트
- 시각 골든 회귀
- Playwright 전체 E2E

원칙:

- fast tier가 빨라야 Ralph가 자주 돌 수 있다.
- slow tier는 무겁더라도 더 높은 신뢰도를 제공한다.
- slow tier 실패는 렌더 파라미터 튜닝 루프로 연결된다.

---

## 3. Step 0: 빌드 복구 + Green Baseline

### 3.1 목표

Ralph Loop을 시작하기 전에 **모든 기존 테스트가 통과하고 빌드가 성공하는 상태**를 만든다.
`--co`(collect only)가 아니라 실제 실행 결과가 green이어야 한다.

### 3.2 수행 작업

#### 3.2.1 Python 의존성 정리

`pyproject.toml`의 `[dev]` extras에 누락된 의존성을 추가한다.

```toml
[project.optional-dependencies]
stt = [
    "torch>=2.0",
    "torchaudio>=2.0",
    "faster-whisper>=1.0",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    # 비디오 QA용 (Slow tier에서 사용)
    "opencv-python-headless>=4.8",
    "scikit-image>=0.22",
    # OCR 감지기용
    "easyocr>=1.7",
]
```

설치 명령:

```bash
./.venv/bin/pip install -e ".[dev]"
```

#### 3.2.2 STT 의존 테스트 격리

`faster-whisper`가 설치되지 않은 환경에서도 fast tier가 통과해야 한다.

skip 범위는 **실제로 모델을 로드하는 테스트만** 최소한으로 잡는다:

- `tests/test_transcriber.py`: `WhisperSTT`를 직접 생성하고 `.transcribe()`를 호출하는 테스트에만 `@pytest.mark.skipif` 추가
- skip 조건: `not importlib.util.find_spec("faster_whisper")`

대상 (skip):
- `tests/test_transcriber.py::TestWhisperSTT.test_transcribe_silent_audio` (모델 로드)
- `tests/test_transcriber.py::TestWhisperSTT.test_transcribe_with_offset` (모델 로드)

fast tier에 유지 (skip하지 않음):
- `tests/test_stt.py::TestTranscriptSegment` — Pydantic 모델 단위 테스트, 모델 로드 없음
- `tests/test_stt.py::TestWhisperSTT.test_init_defaults` — 생성자 기본값 확인, 모델 로드 없음
- `tests/test_stt.py::TestWhisperSTT.test_transcribe_parses_segments` — MagicMock 기반, 모델 로드 없음
- `tests/test_vad.py::TestEnergyVAD` — `SileroVAD._energy_vad()` 정적 메서드 테스트, torch 불필요
- `tests/test_vad.py::TestSileroVAD.test_silent_audio_no_speech` — energy fallback 경로만 타므로 유지 가능

원칙: 유효한 회귀 검증을 숨기지 않는다. MagicMock이나 정적 메서드 테스트는 항상 fast tier에 남긴다.

#### 3.2.3 프론트 빌드 복구

`page.tsx:70`에서 `LeftPanel`에 `transcriptLines` prop을 전달한다.

```tsx
// 수정 전
<LeftPanel onCapture={handleManualCapture} />

// 수정 후
<LeftPanel onCapture={handleManualCapture} transcriptLines={transcriptLines} />
```

#### 3.2.4 프론트 의존성 설치

```bash
cd frontend && npm install
cd frontend && npm install -D @playwright/test
cd frontend && npx playwright install chromium
```

### 3.3 게이트

아래 **두 명령 모두** 0 exit code여야 한다.

```bash
./.venv/bin/python -m pytest tests -q
cd frontend && npm run build
```

실패하는 테스트가 있으면 Ralph는 구현 단계로 진행하지 않는다.

---

## 4. Step 0.5: FE/BE 스키마 통일

### 4.1 목표

프론트엔드와 백엔드의 데이터 계약을 일치시켜, 이후 모든 테스트가 동일한 shape을 기대하게 한다.

### 4.2 Template Enum 통일 — 3개로 고정

```
통일된 템플릿 목록: "blur_fill" | "letterbox" | "cam_split"
```

현재 프론트엔드(`frontend/lib/types.ts:49`)가 이미 이 3개를 사용하고 있으므로, **백엔드를 프론트에 맞춘다**.
`overlay`와 `dynamic`은 editing.md에 설계가 있지만, 현 단계에서는 구현하지 않는다.
추후 필요하면 별도 Axis로 추가한다.

변경:
- `backend/models.py` GenerateRequest: `pattern="^(blur_fill|letterbox|cam_split)$"` (crop 제거)
- `frontend/lib/types.ts` ShortsTemplate: 변경 없음 (이미 3개)
- Playwright 프리뷰 흐름의 "3개 템플릿 카드" 전제와 일치함

### 4.3 GeneratedShort 스키마 보강

`backend/models.py` GeneratedShort에 필드 추가:

```python
class GeneratedShort(BaseModel):
    id: str
    title: str
    thumbnail_url: str = Field(default="", alias="thumbnailUrl")
    artifact_url: str = Field(default="", alias="artifactUrl")
    duration: str
    created_at: str = Field(alias="createdAt")
    indicators: list[IndicatorType]
    template: str = Field(default="blur_fill")
    caption: str = Field(default="")

    model_config = {"populate_by_name": True}
```

### 4.4 단일 계약 (모든 테스트가 믿는 shape)

생성 완료 응답과 WebSocket payload는 동일 shape로 고정한다.

```json
{
  "id": "gs-1234",
  "title": "Ace clutch",
  "thumbnailUrl": "/artifacts/thumbs/gs-1234.jpg",
  "artifactUrl": "/artifacts/videos/gs-1234.mp4",
  "duration": "0:28",
  "createdAt": "방금 전",
  "indicators": ["kill_event", "audio_spike"],
  "template": "blur_fill",
  "caption": "ACE CLUTCH"
}
```

### 4.5 _run_generation() 수정

`backend/server.py`의 `_run_generation()`에서 GeneratedShort 생성 시 `template`, `caption` 전달:

```python
generated = GeneratedShort(
    id=short_id,
    title=title,
    duration=duration,
    created_at="방금 전",
    indicators=indicators,
    template=req.template,
    caption=req.caption,
    artifact_url=f"/artifacts/videos/{short_id}.mp4",
    thumbnail_url=f"/artifacts/thumbs/{short_id}.jpg",
)
```

### 4.6 게이트

```bash
./.venv/bin/python -m pytest tests/test_server.py -v
cd frontend && npm run build
```

기존 서버 테스트와 빌드가 여전히 통과해야 한다.

---

## 5. 사전 설정

### 5.1 부트스트랩 명령

```bash
./.venv/bin/pip install -e ".[dev]"
cd frontend && npm install
cd frontend && npm install -D @playwright/test
cd frontend && npx playwright install chromium
which ffmpeg ffprobe yt-dlp node
```

### 5.2 필수 환경 변수

```bash
LIVEO_TEST_MODE=1
NEXT_PUBLIC_TEST_MODE=1
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/ws/events
```

규칙:

- `LIVEO_TEST_MODE=1` 일 때만 테스트 전용 API 노출
- `NEXT_PUBLIC_TEST_MODE=1` 일 때는 외부 iframe 대신 local placeholder 사용

### 5.3 테스트 디렉토리 부트스트랩

모든 Axis 시작 전에 실행:

```bash
mkdir -p tests/api tests/detectors tests/video tests/integration
touch tests/api/__init__.py tests/api/conftest.py
touch tests/detectors/__init__.py
touch tests/video/__init__.py tests/video/conftest.py
touch tests/integration/__init__.py
mkdir -p frontend/tests/e2e
```

---

## 6. 구현 원칙

### 6.1 테스트를 먼저 고정할 축

Ralph는 아래 순서로 테스트 기반을 만든다.

1. 빌드 복구 + green baseline (Step 0)
2. FE/BE 스키마 통일 (Step 0.5)
3. 테스트 격리와 test mode API
4. 핵심 사용자 흐름 (Twitch URL -> 대시보드 -> 백엔드 연결)
5. 백엔드 API / WS 계약
6. 프런트 상태/액션 실연결
7. 프런트 testability + Playwright
8. 감지기 / 렌더 구현
9. 파이프라인 통합
10. 비디오 QA

### 6.2 테스트 가능성을 위한 제품 코드 변경

아래 변경은 "테스트 코드"가 아니라 제품 코드에 포함돼야 한다.

- `backend/server.py`
  - 테스트 전용 reset/seed/event API 추가 (`LIVEO_TEST_MODE=1` 시에만 노출)
  - `GeneratedShort` 응답 스키마를 프런트와 일치시킴 (Step 0.5에서 완료)
  - 생성 완료 시 `artifactUrl`, `thumbnailUrl`, `template`, `caption`, `createdAt` 반환
  - `/artifacts` 정적 파일 서빙 마운트 추가:
    ```python
    from starlette.staticfiles import StaticFiles
    from pathlib import Path

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    (artifacts_dir / "videos").mkdir(exist_ok=True)
    (artifacts_dir / "thumbs").mkdir(exist_ok=True)

    app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")
    ```
  - `LIVEO_TEST_MODE=1`일 때 `FakeCapture` 사용 (Section 2.4 참조)
  - `LIVEO_TEST_MODE=1`일 때 `_run_generation()`에서 fake artifact 생성 (Section 2.4 참조)
- `frontend/lib/use-liveo.ts` (신규 생성)
  - 초기 로드 시 `GET /api/stream/status`, `GET /api/shorts/candidates`, `GET /api/shorts`, `GET /api/settings` bootstrap
  - WebSocket은 이후 delta update만 반영 — **transcript_update, indicator_update 이벤트도 포함**
  - 반환 상태에 `transcriptLines: TranscriptLine[]`과 `indicators: Indicator[]` 포함
  - `transcript_update` WS 이벤트 → `transcriptLines` 배열에 append
  - `indicator_update` WS 이벤트 → 해당 indicator의 `value`, `active` 갱신
  - 연결 끊김 시 exponential backoff reconnect
- `frontend/lib/use-websocket.ts` → `use-liveo.ts`가 내부에서 래핑한다 (use-websocket.ts는 WS 연결 전용으로 유지)
- `frontend/components/indicators/IndicatorDashboard.tsx`
  - `import { indicators } from "@/lib/mock-data"` 제거
  - `indicators` props 또는 `use-liveo.ts` 훅 상태로 렌더
  - 스트림 미시작 시 기본값 (모든 indicator value=0, active=false) 표시
- `frontend/components/shorts/GeneratedShortsGrid.tsx`
  - `mock-data.ts` import 제거, `generatedShorts` props 또는 훅 상태로 렌더
- `frontend/components/shorts/ShortsCandidateCard.tsx`
  - CONFIRM/SKIP에 `PATCH /api/shorts/candidates/{id}` 연결
  - UNDO에 `PATCH /api/shorts/candidates/{id} { status: "pending" }` 연결
- `frontend/components/shorts/ShortsPreviewModal.tsx`
  - GENERATE ALL 버튼에 `POST /api/shorts/generate` 호출 연결
- `frontend/components/shorts/GeneratedShortsGrid.tsx`
  - DOWNLOAD 버튼에 `artifactUrl` 다운로드 핸들러 연결
- `frontend/components/stream/StreamEmbed.tsx`
  - `NEXT_PUBLIC_TEST_MODE=1`이면 외부 iframe 대신 deterministic placeholder 렌더
  - 정상 모드: `streamUrl` prop을 받아 해당 채널 iframe 렌더 (하드코딩 제거)
- `frontend/components/landing/LandingScreen.tsx`
  - Enter 시 `POST /api/stream/start` 호출 추가
- 주요 인터랙션 컴포넌트에 `data-testid` 추가

### 6.3 data-testid 목록

```
data-testid="landing-url-input"
data-testid="landing-connect-button"  (Enter 키 대체용)
data-testid="stream-embed"
data-testid="stream-placeholder"  (test mode)
data-testid="indicator-dashboard"
data-testid="manual-capture-button"
data-testid="transcript-feed"
data-testid="candidate-card-{id}"
data-testid="candidate-confirm-{id}"
data-testid="candidate-skip-{id}"
data-testid="candidate-undo-{id}"
data-testid="candidate-preview-{id}"
data-testid="preview-modal"
data-testid="preview-generate-all"
data-testid="preview-cancel"
data-testid="generated-shorts-grid"
data-testid="short-bundle-{title}"
data-testid="short-download-{id}"
data-testid="settings-button"
data-testid="settings-modal"
data-testid="header-session-timer"
data-testid="header-shorts-count"
```

---

## 7. 테스트 구조

### 7.1 테스트 격리 전략

#### 백엔드 상태 초기화

`tests/conftest.py`:

```python
import backend.server as srv

@pytest.fixture(autouse=True)
def _reset_server_state():
    """매 테스트 전에 서버 전역 상태를 초기화한다."""
    srv._candidates.clear()
    srv._generated.clear()
    srv._settings = srv.Settings()
    srv._pipeline = None
    srv._transcript_proc = None
    srv._start_time = 0
    srv._capture_method = ""
    srv._error = None
    yield
```

#### STT 의존 테스트 skip

```python
import importlib.util

requires_whisper = pytest.mark.skipif(
    not importlib.util.find_spec("faster_whisper"),
    reason="faster-whisper not installed (optional STT dependency)"
)

requires_torch = pytest.mark.skipif(
    not importlib.util.find_spec("torch"),
    reason="torch not installed (optional STT dependency)"
)
```

### 7.2 백엔드 API 계약 테스트

신규 생성 파일:

- `tests/api/conftest.py` -- ASGI client fixture, state reset
- `tests/api/test_stream_api.py`
- `tests/api/test_candidates_api.py`
- `tests/api/test_generation_api.py`
- `tests/api/test_settings_api.py`
- `tests/api/test_websocket.py`
- `tests/api/test_testmode_api.py`

#### tests/api/conftest.py

```python
import pytest
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient

import backend.server as srv
from backend.server import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.fixture
def ws_client():
    """WebSocket 테스트용 동기 TestClient."""
    return TestClient(app)
```

#### WebSocket 테스트 방법론

FastAPI의 WebSocket 테스트는 `starlette.testclient.TestClient`를 사용한다.

```python
def test_candidate_created_broadcasts_ws(ws_client, client):
    with ws_client.websocket_connect("/ws/events") as ws:
        # HTTP로 후보 생성
        response = client.post("/api/shorts/candidates", json={...})
        # WS에서 이벤트 수신
        data = ws.receive_json()
        assert data["type"] == "candidate_created"
        assert "id" in data["data"]
```

#### 핵심 검증 항목

**test_stream_api.py:**
- `POST /api/stream/start` source="demo" + url -> 200 + isLive=True
- `POST /api/stream/start` source="demo" url 미제공 -> 400
- `POST /api/stream/start` 중복 호출 -> 400
- `POST /api/stream/stop` -> isLive=False
- `GET /api/stream/status` -> 정상 shape 반환

**test_candidates_api.py:**
- CRUD 전체 사이클 (create -> list -> patch -> delete)
- confirm/dismiss 상태 전이
- 없는 candidate_id -> 404

**test_generation_api.py:**
- generate 호출 -> jobId + status="generating" 반환
- 없는 candidate -> 404
- generate_complete 이벤트에 `artifactUrl`, `template`, `caption` 포함 확인
- `GET /api/shorts` 결과에 생성 결과 포함 확인

**test_settings_api.py:**
- GET -> 기본값 반환
- PATCH -> 변경값 반영
- round-trip 일관성

**test_websocket.py:**
- 연결/해제 lifecycle
- candidate_created / candidate_updated / candidate_deleted 이벤트 shape
- generate_progress 이벤트 순서 (10 -> 30 -> 50 -> 70 -> 90 -> 100)
- generate_complete 이벤트 payload shape (단일 계약 일치)
- stream_status 이벤트

**test_testmode_api.py:**
- `LIVEO_TEST_MODE=1`일 때만 `/api/test/reset`, `/api/test/seed`, `/api/test/events` 접근 가능
- reset -> 모든 상태 초기화
- seed -> 미리 정의된 테스트 데이터 주입
- events -> 지정한 WS 이벤트 강제 발행

### 7.3 감지기 테스트

파일:

- `tests/detectors/test_audio_excitement.py`
- `tests/detectors/test_keyword_detector.py`
- `tests/detectors/test_killfeed_ocr.py`
- `tests/detectors/test_highlight_aggregator.py`

검증:

- audio spike: EMA 기반 RMS, 기준선 대비 3-sigma 이상 spike 감지
- keyword: 영어 하이라이트 키워드 (ace, clutch, insane 등) 스코어
- OCR: Valorant 킬피드 ROI 추출과 kill event 감지
- aggregator: 가중합 (audio 30% + keyword 30% + killfeed 40%) + threshold >= 0.6

OCR 의존성: `easyocr`은 `[dev]` extras에 포함. GPU 없이도 CPU 모드로 동작한다.

### 7.4 렌더 및 비디오 QA

파일:

- `tests/video/conftest.py`
- `tests/video/frame_utils.py`
- `tests/video/metrics.py`
- `tests/video/test_output_spec.py`
- `tests/video/test_crop_and_layout.py`
- `tests/video/test_visual_goldens.py`
- `tests/video/test_continuity.py`
- `tests/video/test_shortform_envelope.py`

#### tests/video/conftest.py

```python
import subprocess
import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def ffmpeg_available():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        pytest.skip("ffmpeg not available")

@pytest.fixture(scope="session")
def test_video_fixture(tmp_path_factory, ffmpeg_available):
    """3초짜리 deterministic 테스트 영상을 ffmpeg으로 생성한다."""
    out = tmp_path_factory.mktemp("fixtures") / "test_input.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-c:a", "aac",
        str(out)
    ], check=True, capture_output=True)
    return str(out)

GOLDEN_DIR = Path(__file__).parent / "goldens"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
```

#### test_output_spec.py -- 구체적 게이트 기준

```python
def test_output_spec(rendered_video):
    probe = ffprobe(rendered_video)

    assert probe["width"] == 1080
    assert probe["height"] == 1920
    assert probe["display_aspect_ratio"] == "9:16"
    assert probe["video_codec"] == "h264"
    assert probe["audio_codec"] == "aac"
    assert 15.0 <= probe["duration_sec"] <= 30.0

    # artifact 파일 존재 확인
    assert Path(rendered_video).exists()
    thumb = rendered_video.replace(".mp4", "_thumb.jpg")
    assert Path(thumb).exists()
```

#### test_continuity.py -- 구체적 임계치

| 메트릭 | 계산 방법 | 임계치 | 실패 시 조정 |
|--------|---------|--------|-------------|
| freeze frame | 연속 프레임 간 SSIM > 0.99인 구간의 최대 길이 | <= 0.5초 | `clip_editor.py`의 scene 선택 로직 수정 |
| crop center jump | 인접 프레임 크롭 중심점의 유클리드 거리 최대값 | <= 50px/frame | 크롭 smoothing factor 증가 |
| black frame ratio | 평균 luminance < 10인 프레임 비율 | <= 3% | pre-buffer 시작점 조정 |
| overlay fade | 오버레이 등장/퇴장 전환 프레임 수 | 60~90 frames (2~3초) | fade duration 파라미터 조정 |

```python
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

def test_no_freeze_frames(rendered_video):
    """0.5초(15 frames @30fps) 이상 동일 프레임 없음."""
    cap = cv2.VideoCapture(rendered_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    max_freeze_frames = int(fps * 0.5)

    prev = None
    consecutive = 0
    max_consecutive = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            score = ssim(prev, gray)
            if score > 0.99:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0
        prev = gray

    cap.release()
    assert max_consecutive <= max_freeze_frames, (
        f"Freeze detected: {max_consecutive} frames "
        f"({max_consecutive/fps:.1f}s), limit is {max_freeze_frames} "
        f"({max_freeze_frames/fps:.1f}s). "
        f"Adjust: clip_editor scene selection or segment boundary."
    )
```

#### test_shortform_envelope.py -- 구체적 수치와 조정 포인트

**외부 샘플에서 계산할 지표 (기준선):**

현재 `resources/samples/`에는 프레임 이미지만 있으므로, spatial metric만 사용한다.
temporal metric은 내부 골든 대비로만 계산한다.

| 메트릭 | 계산 방법 | 허용 범위 | 실패 시 조정 |
|--------|---------|---------|-------------|
| motion energy | 인접 프레임 절대 차이 합의 평균 (per-frame) | >= 500 (8bit, 1080x1920 기준) | 정적 구간 제거 또는 scene 재선택 |
| dead-air ratio | motion energy < 100인 프레임 비율 | <= 20% | pre/post buffer 축소 |
| subject center bias | 프레임 중앙 40% 영역의 edge density / 전체 대비 | >= 1.3x | 크롭 중심점 재계산 |
| first-3s hook | 처음 3초 평균 motion energy / 전체 평균 | >= 0.8x | highlight timestamp 앞으로 이동 |
| text occupancy | OCR로 감지된 텍스트 영역 / 전체 프레임 | <= 15% | 오버레이 축소 또는 위치 조정 |

```python
def test_motion_energy_above_minimum(rendered_video):
    frames = extract_frames(rendered_video)
    energies = []
    for i in range(1, len(frames)):
        diff = np.abs(frames[i].astype(float) - frames[i-1].astype(float))
        energies.append(diff.sum() / (frames[i].shape[0] * frames[i].shape[1]))

    avg_energy = np.mean(energies)
    assert avg_energy >= 500, (
        f"Motion energy too low: {avg_energy:.0f} (minimum 500). "
        f"Adjust: Remove static pre/post buffer or select higher-action segment."
    )

def test_dead_air_ratio(rendered_video):
    frames = extract_frames(rendered_video)
    dead = sum(1 for i in range(1, len(frames))
               if frame_energy(frames[i], frames[i-1]) < 100)
    ratio = dead / max(1, len(frames) - 1)
    assert ratio <= 0.20, (
        f"Dead-air ratio {ratio:.1%} exceeds 20%. "
        f"Adjust: Shrink pre_buffer from 5s to 3s in clip_editor.py"
    )
```

#### 비디오 fixture 전략

deterministic 입력 영상은 ffmpeg의 `testsrc` + `sine` filter로 생성한다.
이 fixture는 `tests/video/conftest.py`의 `test_video_fixture`에서 자동 생성된다.

실제 게임 영상 fixture는 다음 방법으로 추가한다:
1. 짧은 5초 게임 영상을 `resources/fixtures/game_clip_5s.mp4`에 저장
2. `conftest.py`에서 fixture가 있으면 사용, 없으면 `testsrc` fallback
3. CI에서는 항상 `testsrc` fallback 사용 (게임 영상 미포함)

### 7.5 Playwright E2E

위치: `frontend/tests/e2e/`

파일:

- `frontend/playwright.config.ts`
- `frontend/tests/e2e/landing.spec.ts`
- `frontend/tests/e2e/manual-capture.spec.ts`
- `frontend/tests/e2e/candidate-lifecycle.spec.ts`
- `frontend/tests/e2e/preview-modal.spec.ts`
- `frontend/tests/e2e/reload-reconnect.spec.ts`
- `frontend/tests/e2e/download-verify.spec.ts`
- `frontend/tests/e2e/visual.spec.ts`

#### playwright.config.ts -- 핵심 설정

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL: "http://localhost:3000",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: "LIVEO_TEST_MODE=1 ../.venv/bin/python -m backend --serve",
      url: "http://localhost:8000/api/stream/status",
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
    },
    {
      command: "NEXT_PUBLIC_TEST_MODE=1 NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
```

**핵심**: `webServer` 배열로 백엔드(8000)와 프론트(3000)를 동시에 기동한다.

#### Playwright 테스트 시나리오

**landing.spec.ts** `@fast`:
- 랜딩 페이지 로드 -> URL 입력 필드 노출
- URL 입력 후 Enter -> `POST /api/stream/start` 호출 확인 (네트워크 intercept)
- 대시보드 전환 -> stream embed, indicator dashboard, transcript feed 노출

**manual-capture.spec.ts** `@fast`:
- spacebar 또는 버튼 hold -> 캡처 동작
- hold 해제 -> 후보 카드 생성 확인

**candidate-lifecycle.spec.ts** `@fast`:
- `/api/test/seed`로 후보 주입
- CONFIRM 버튼 -> 상태 "confirmed" 전환 확인
- SKIP 버튼 -> 상태 "dismissed" 전환 확인
- UNDO 버튼 -> 상태 "pending" 복원 확인
- PREVIEW 버튼 -> 모달 열림 확인

**preview-modal.spec.ts** `@fast`:
- 모달에서 3개 템플릿 카드 노출 확인
- GENERATE ALL -> `POST /api/shorts/generate` 호출 확인
- progress bar 반영 확인
- 완료 후 generated shorts grid에 반영 확인

**download-verify.spec.ts**:
- 생성 완료 후 DOWNLOAD 버튼 클릭
- `download` 이벤트 발생 확인
- 다운로드된 파일에 `ffprobe` 실행하여 스펙 검증:
  ```typescript
  const download = await downloadPromise;
  const filePath = await download.path();
  const { stdout } = await exec(
    `ffprobe -v quiet -print_format json -show_format -show_streams "${filePath}"`
  );
  const probe = JSON.parse(stdout);
  expect(probe.streams[0].width).toBe(1080);
  expect(probe.streams[0].height).toBe(1920);
  ```

**reload-reconnect.spec.ts** `@fast`:
- `/api/test/seed`로 상태 주입
- 새로고침
- bootstrap GET으로 상태 복구 확인 (stream status, candidates, generated shorts)
- WebSocket 재연결 확인

**visual.spec.ts**:
- `/api/test/seed`로 deterministic 상태 주입
- 대시보드 스크린샷
- 시간, 랜덤 ID, 실시간 숫자를 mask
- 외부 iframe 대신 test mode placeholder 사용
- golden screenshot과 비교

#### Playwright 안정화 규칙

- 외부 iframe: `NEXT_PUBLIC_TEST_MODE=1`이면 placeholder로 대체
- 애니메이션: `page.emulateMedia({ reducedMotion: "reduce" })`
- 시간/ID mask: `expect(page).toHaveScreenshot({ mask: [selector1, selector2] })`
- visual spec: deterministic seed + test mode에서만 실행

### 7.6 Fast Tier와 Slow Tier 명령

`frontend/package.json`에 추가할 스크립트:

```json
{
  "scripts": {
    "test:fast": "playwright test --grep @fast",
    "test:e2e": "playwright test",
    "test:visual": "playwright test visual.spec.ts"
  }
}
```

Fast tier 전체 명령:

```bash
# 백엔드 (STT 의존 테스트 자동 skip)
./.venv/bin/python -m pytest tests/test_capture.py tests/test_events.py tests/test_pipeline.py tests/test_ring_buffer.py tests/test_server.py tests/api tests/detectors -q

# 프런트
cd frontend && npm run test:fast
cd frontend && npm run build
```

Slow tier 전체 명령:

```bash
./.venv/bin/python -m pytest tests/video -v
cd frontend && npm run test:e2e
cd frontend && npm run test:visual
```

---

## 8. 구현 축별 세부 계획

### Axis 1: Test Mode / State Reset / FakeCapture

**Precondition:** Step 0, Step 0.5 완료. `tests/api/` 디렉토리 생성.

구현:

- `backend/capture.py` -- `FakeCapture` 클래스 추가
- `backend/server.py` -- 테스트 전용 엔드포인트 + FakeCapture 분기 + artifact 정적 서빙 + fake generation
- `tests/conftest.py` -- autouse fixture로 전역 상태 초기화 + `LIVEO_TEST_MODE=1` 설정
- `tests/api/conftest.py` -- ASGI client + WS client fixture
- `tests/api/test_testmode_api.py`

작업:

- `backend/capture.py`에 `FakeCapture(BaseCapture)` 추가 (Section 2.4 코드 그대로)
- `backend/server.py` `stream_start()`에서 `LIVEO_TEST_MODE=1` 분기: FakeCapture 사용, Pipeline/TranscriptProcessor 생성 생략
- `backend/server.py`에 `app.mount("/artifacts", StaticFiles(...))` 추가
- `backend/server.py` `_run_generation()`에서 `LIVEO_TEST_MODE=1` 분기: ffmpeg으로 1초짜리 fake 영상/썸네일 생성
- `LIVEO_TEST_MODE=1` 환경변수 분기
- `POST /api/test/reset` -- 모든 전역 상태 초기화 + artifacts 디렉토리 정리
- `POST /api/test/seed` -- 미리 정의된 후보/생성 결과 주입. Payload:
  ```json
  {
    "candidates": [
      {
        "title": "Test Highlight",
        "status": "pending",
        "confidence": 0.85,
        "indicators": ["audio_spike", "keyword"],
        "timestamp_start": 10.0,
        "timestamp_end": 25.0
      }
    ],
    "generated": [
      {
        "id": "gs-test-1",
        "title": "Test Short",
        "duration": "0:15",
        "indicators": ["audio_spike"],
        "template": "blur_fill",
        "caption": "TEST"
      }
    ]
  }
  ```
- `POST /api/test/events` -- 지정한 WS 이벤트 강제 발행
- `tests/conftest.py`에 autouse fixture로 매 테스트 전 상태 초기화 + `LIVEO_TEST_MODE=1` 환경 설정

종료 조건:

```bash
LIVEO_TEST_MODE=1 ./.venv/bin/python -m pytest tests/api/test_testmode_api.py -v
```

### Axis 2: 핵심 사용자 흐름 (Twitch URL -> 대시보드)

**Precondition:** Axis 1 완료.

구현:

- `frontend/components/landing/LandingScreen.tsx` -- Enter 시 API 호출 추가
- `frontend/components/stream/StreamEmbed.tsx` -- URL prop 수용 + test mode placeholder
- `frontend/app/page.tsx` -- streamUrl을 StreamEmbed에 전달
- `backend/server.py` -- stream start 성공 케이스 테스트 보강

작업:

- LandingScreen: Enter 시 `POST /api/stream/start { source: "demo", url: userInputUrl }` 호출
- 성공 시 `setStreamUrl(url)` + 대시보드 전환
- 실패 시 에러 메시지 표시
- StreamEmbed: `streamUrl` prop -> Twitch player URL 동적 생성
- StreamEmbed: `NEXT_PUBLIC_TEST_MODE=1` -> `<div data-testid="stream-placeholder">` 렌더
- data-testid 추가: `landing-url-input`, `stream-embed`, `stream-placeholder`

주의:
- `test_stream_api.py`에서 `POST /api/stream/start`는 FakeCapture를 통해 실행된다 (Axis 1에서 설정)
- 실제 ffmpeg/yt-dlp 프로세스가 spawn되지 않으므로 네트워크 없이 통과한다

종료 조건:

```bash
cd frontend && npm run build
# FakeCapture 기반 stream start 테스트 (네트워크 불필요)
LIVEO_TEST_MODE=1 ./.venv/bin/python -m pytest tests/api/test_stream_api.py -v
```

### Axis 3: Backend API / WS 계약 고정

**Precondition:** Axis 1 완료.

구현:

- `tests/api/test_stream_api.py`
- `tests/api/test_candidates_api.py`
- `tests/api/test_generation_api.py`
- `tests/api/test_settings_api.py`
- `tests/api/test_websocket.py`

작업:

- 모든 API 엔드포인트의 정상/에러 케이스 테스트
- WebSocket 이벤트 shape 검증 (Section 7.2 참조)
- generate_complete payload가 단일 계약(Section 4.4)과 일치하는지 검증

종료 조건:

```bash
./.venv/bin/python -m pytest tests/api -v
```

### Axis 4: Frontend State / Actions 실연결

**Precondition:** Axis 2, 3 완료.

구현:

- `frontend/lib/use-liveo.ts` (신규)
- `frontend/app/page.tsx`
- `frontend/components/shorts/GeneratedShortsGrid.tsx`
- `frontend/components/shorts/ShortsCandidateCard.tsx`
- `frontend/components/shorts/ShortsPreviewModal.tsx`
- `frontend/components/indicators/IndicatorDashboard.tsx`

작업:

- `use-liveo.ts` 신규 생성: bootstrap GET + WS delta (transcript_update, indicator_update 포함) + reconnect
- `page.tsx`: `mock-data.ts` import 전부 제거 (`shortsCandidates`, `transcriptLines`), `use-liveo.ts` 훅으로 교체
- `IndicatorDashboard.tsx`: `import { indicators } from "@/lib/mock-data"` 제거, props 또는 훅 상태로 교체
- `GeneratedShortsGrid.tsx`: `mock-data.ts` import 제거, props/훅 상태로 렌더
- `ShortsCandidateCard.tsx`: CONFIRM -> `PATCH status: "confirmed"`, SKIP -> `PATCH status: "dismissed"`, UNDO -> `PATCH status: "pending"`
- `ShortsPreviewModal.tsx`: GENERATE ALL -> 3개 템플릿으로 `POST /api/shorts/generate` 호출
- `GeneratedShortsGrid.tsx`: DOWNLOAD -> `artifactUrl`로 `<a download>` 또는 `fetch + blob`

종료 조건:

```bash
cd frontend && npm run build
```

### Axis 5: Frontend Testability / Playwright

**Precondition:** Axis 4 완료. Playwright 설치 완료.

구현:

- `frontend/components/**` -- data-testid 추가
- `frontend/playwright.config.ts` -- webServer 2개 설정
- `frontend/tests/e2e/**` -- 모든 spec 파일

작업:

- Section 6.3의 data-testid 전부 추가
- test mode placeholder 동작 확인
- visual mask 규칙 적용
- `@fast` 태그 핵심 흐름 spec 작성
- download-verify spec 작성 (ffprobe 검증)

종료 조건:

```bash
cd frontend && npm run test:fast
cd frontend && npm run test:e2e
```

### Axis 6: Highlight Detection

**Precondition:** `tests/detectors/` 디렉토리 생성. `easyocr` 설치 완료.

구현:

- `backend/detectors/__init__.py`
- `backend/detectors/audio_excitement.py`
- `backend/detectors/keyword.py`
- `backend/detectors/killfeed_ocr.py`
- `backend/highlight_aggregator.py`

참고:

- `backend/docs/transcript.md`

종료 조건:

```bash
./.venv/bin/python -m pytest tests/detectors -v
```

### Axis 7: Clip Editor (실제 렌더)

**Precondition:** Axis 6 완료. ffmpeg 설치 확인.

구현:

- `backend/clip_editor.py`

참고:

- `backend/docs/editing.md`

작업:

- blur_fill / letterbox / cam_split 3개 템플릿 지원 (overlay, dynamic은 이번 범위에서 제외)
- 입력: ring buffer 세그먼트 경로 + 시간 범위 + 템플릿
- 출력: artifact video (.mp4), thumbnail (.jpg)
- zoom/slow-motion 이펙트 (editing.md 참조)
- 렌더 결과 metadata 저장

종료 조건:

```bash
./.venv/bin/python -m pytest tests/video/test_output_spec.py tests/video/test_crop_and_layout.py -v
```

### Axis 8: Pipeline Integration

**Precondition:** Axis 6, 7 완료.

구현:

- `backend/pipeline.py` -- 감지기 호출 통합
- `backend/server.py` -- _run_generation()에서 clip_editor 실행
- `tests/integration/test_pipeline_integration.py`

작업:

- 세그먼트 -> 감지기 호출 (audio + keyword + OCR)
- highlight -> 후보 자동 생성 (threshold >= 0.6)
- generate 요청 -> 실제 clip_editor 실행 -> artifact 파일 생성
- artifact 경로를 GeneratedShort에 반영

종료 조건:

```bash
./.venv/bin/python -m pytest tests/integration/test_pipeline_integration.py -v
```

### Axis 9: Slow Tier Video QA

**Precondition:** Axis 7, 8 완료. `opencv-python-headless`, `scikit-image` 설치.

구현:

- `tests/video/**`
- 내부 골든 asset (`tests/video/goldens/`)

작업:

- deterministic fixture 생성 (ffmpeg testsrc)
- visual golden 비교 (SSIM >= 0.85)
- continuity 검증 (Section 7.4 임계치)
- shortform envelope 검증 (Section 7.4 수치)

종료 조건:

```bash
./.venv/bin/python -m pytest tests/video -v
```

---

## 9. 최종 Acceptance Criteria

Ralph Loop는 아래 AC를 모두 통과할 때까지 종료하지 않는다.

### AC-1 Green Baseline

기존 테스트 전체 통과 + 빌드 성공.

```bash
./.venv/bin/python -m pytest tests -q
cd frontend && npm run build
```

**주의:** `--co`가 아니라 실제 실행. STT 의존 테스트는 skip되어도 0 failures.

### AC-2 테스트 모드 API 정상

```bash
LIVEO_TEST_MODE=1 ./.venv/bin/python -m pytest tests/api/test_testmode_api.py -v
```

### AC-3 API / WebSocket 계약 전체 통과

```bash
./.venv/bin/python -m pytest tests/api -v
```

### AC-4 Fast Tier 전체 통과

```bash
./.venv/bin/python -m pytest tests/test_capture.py tests/test_events.py tests/test_pipeline.py tests/test_ring_buffer.py tests/test_server.py tests/api tests/detectors -q
cd frontend && npm run test:fast
cd frontend && npm run build
```

### AC-5 핵심 사용자 흐름 동작

Twitch URL 입력 -> 백엔드 호출 -> 대시보드 전환이 E2E로 검증됨.

검증 항목:

- Landing에서 URL 입력 후 Enter -> POST /api/stream/start 호출
- 대시보드에 stream embed, indicators, transcript 노출
- candidate confirm / dismiss / undo 동작
- generate 요청 + progress 반영
- generate_complete 이후 Generated Shorts 영역 갱신
- 새로고침 후 bootstrap 복구
- DOWNLOAD 클릭 -> 파일 다운로드 + ffprobe 스펙 확인

검증 명령:

```bash
cd frontend && npm run test:e2e
```

### AC-6 출력 영상 스펙 충족

```bash
./.venv/bin/python -m pytest tests/video/test_output_spec.py -v
```

통과 조건:

- 1080x1920
- H.264 / AAC
- 15~30초
- artifact .mp4 + thumbnail .jpg 존재

### AC-7 레이아웃 / 크롭 / continuity 통과

```bash
./.venv/bin/python -m pytest tests/video/test_crop_and_layout.py tests/video/test_continuity.py -v
```

### AC-8 레퍼런스 기반 shortform envelope 통과

```bash
./.venv/bin/python -m pytest tests/video/test_shortform_envelope.py -v
```

필수 체크 (구체적 수치):

- dead-air ratio <= 20%
- freeze frame <= 0.5초
- motion energy >= 500
- first-3s hook >= 0.8x 평균
- text occupancy <= 15%

### AC-9 내부 골든 + Playwright visual 회귀 통과

```bash
./.venv/bin/python -m pytest tests/video/test_visual_goldens.py -v
cd frontend && npm run test:visual
```

### AC-10 최종 핵심 흐름 통과

시나리오:

`seed -> 후보 생성 -> confirm -> generate -> artifact 생성 -> UI 반영 -> download 검증 -> reload 복구`

검증 명령:

```bash
./.venv/bin/python -m pytest tests/integration/test_pipeline_integration.py -v
cd frontend && npm run test:e2e
```

---

## 10. Ralph Loop 실행 순서

```text
Step 0.   빌드 복구 + Green Baseline
Step 0.5. FE/BE 스키마 통일
Step 1.   Test mode / state reset (Axis 1)
Step 2.   핵심 사용자 흐름 -- Twitch URL -> 대시보드 (Axis 2)
Step 3.   API / WS 계약 고정 (Axis 3)
Step 4.   Frontend state/actions 실연결 (Axis 4)
Step 5.   Playwright fast tier 작성 및 안정화 (Axis 5)
Step 6.   Highlight detection 구현 (Axis 6)
Step 7.   Clip editor 구현 (Axis 7)
Step 8.   Pipeline integration 연결 (Axis 8)
Step 9.   Slow tier video QA 작성 (Axis 9)
Step 10.  전체 AC 재실행
```

반복 규칙:

- Step 0 gate 실패 -> 즉시 수정. 다음 Step으로 진행하지 않음.
- fast tier 실패 시 즉시 해당 축으로 복귀
- slow tier 실패 시 `실패 시 조정` 컬럼의 지시에 따라 파라미터 튜닝 후 재실행
- 외부 샘플은 항상 envelope 계산용으로만 사용
- internal golden 갱신은 의도적 변경일 때만 허용

---

## 11. 핵심 파일 참조

| 용도 | 파일 |
|------|------|
| PRD | `docs/PRD.md` |
| 스트리밍 설계 | `backend/docs/streaming.md` |
| 감지 설계 | `backend/docs/transcript.md` |
| 편집 설계 | `backend/docs/editing.md` |
| 서버 진입점 | `backend/__main__.py` |
| 서버 구현 | `backend/server.py` |
| 데이터 모델 | `backend/models.py` |
| 파이프라인 | `backend/pipeline.py` |
| WS 매니저 | `backend/ws_manager.py` |
| STT | `backend/stt.py` |
| VAD | `backend/vad.py` |
| 트랜스크립트 | `backend/transcript.py` |
| 프론트 상태 훅 | `frontend/lib/use-liveo.ts` (신규) |
| WS 훅 | `frontend/lib/use-websocket.ts` (기존) |
| 타입 정의 | `frontend/lib/types.ts` |
| 랜딩 화면 | `frontend/components/landing/LandingScreen.tsx` |
| 스트림 임베드 | `frontend/components/stream/StreamEmbed.tsx` |
| 후보 카드 | `frontend/components/shorts/ShortsCandidateCard.tsx` |
| 생성 결과 그리드 | `frontend/components/shorts/GeneratedShortsGrid.tsx` |
| 프리뷰 모달 | `frontend/components/shorts/ShortsPreviewModal.tsx` |
| 레퍼런스 인덱스 | `resources/thumbnail-references.md` |
| 외부 샘플 프레임 | `resources/samples/*` |

---

## 12. 끊김 방지 체크리스트

- [ ] `./.venv/bin/pip install -e ".[dev]"` 완료
- [ ] `cd frontend && npm install && npm install -D @playwright/test` 완료
- [ ] `npx playwright install chromium` 완료
- [ ] `./.venv/bin/python -m pytest tests -q` 0 failures (STT skip OK)
- [ ] `cd frontend && npm run build` 성공
- [ ] `GeneratedShort` 모델에 `template`, `caption`, `artifactUrl` 추가됨
- [ ] Template enum FE/BE 통일 (`blur_fill|letterbox|cam_split` 3개)
- [ ] `FakeCapture` 클래스가 `backend/capture.py`에 존재
- [ ] `LIVEO_TEST_MODE=1`에서 stream start가 FakeCapture를 사용
- [ ] `LIVEO_TEST_MODE=1`에서 generation이 fake artifact를 생성
- [ ] `app.mount("/artifacts", StaticFiles(...))` 서버에 추가됨
- [ ] `IndicatorDashboard.tsx`에서 mock-data import 제거됨
- [ ] `use-liveo.ts`가 transcript_update, indicator_update WS 이벤트를 처리
- [ ] `LIVEO_TEST_MODE=1` / `NEXT_PUBLIC_TEST_MODE=1` 사용
- [ ] 테스트 전용 API는 test mode에서만 노출
- [ ] 외부 iframe을 Playwright에서 사용하지 않음
- [ ] `tests/conftest.py`에 autouse state reset fixture 존재
- [ ] `playwright.config.ts`에 webServer 2개 설정 (BE 8000 + FE 3000)
- [ ] data-testid가 Section 6.3 목록 전체에 부착됨
- [ ] 외부 샘플은 envelope 계산용으로만 사용
- [ ] 내부 골든은 deterministic fixture에만 사용
- [ ] 비디오 QA 임계치가 Section 7.4 수치로 고정됨

---

## 13. v4 -> v5 변경 요약

| 영역 | v4 | v5 |
|------|----|----|
| 캡처 테스트 전략 | 실제 ffmpeg/yt-dlp에 의존 | `FakeCapture` 클래스 + `LIVEO_TEST_MODE=1` 분기 |
| transcript/indicator | `use-liveo.ts`에서 미포함, mock 의존 유지 | WS의 `transcript_update`, `indicator_update` 처리 + `IndicatorDashboard` mock 제거 |
| Template enum | 5개 (`blur_fill\|letterbox\|cam_split\|overlay\|dynamic`) | 3개로 고정 (`blur_fill\|letterbox\|cam_split`), 프론트 기존 타입 유지 |
| STT skip 범위 | `test_stt.py`, `test_transcriber.py`, `test_vad.py` 광범위 skip | `test_transcriber.py`의 모델 로드 테스트 2건만 skip, 나머지 fast tier 유지 |
| artifact 서빙 | 미명시 (URL만 정의, 서빙 코드 없음) | `StaticFiles` 마운트 + fake artifact 생성 전략 명시 |
| `POST /api/test/seed` | payload 미정의 | JSON payload 구조 고정 |
| `use-websocket.ts` 처리 | "통합되거나 래핑" 미결정 | `use-liveo.ts`가 래핑, `use-websocket.ts`는 WS 전용으로 유지 |
| generation mock | 진행률만 mock | ffmpeg으로 1초짜리 fake 9:16 영상 + 썸네일 생성 |

### v3 -> v4 변경 요약 (이전 버전 참고용)

| 영역 | v3 | v4 |
|------|----|----|
| Step 0 게이트 | `pytest --co` + `npm run build` | 실제 `pytest` 0 failures + `npm run build` |
| 스키마 통일 | Axis 2에 암시적 포함 | Step 0.5로 독립 분리, 구체적 diff 명시 |
| use-liveo.ts | 기존 파일 수정으로 기술 | 신규 파일 생성으로 명확화 |
| Template enum | 불일치 미언급 | FE/BE 통일 명시 |
| source 문자열 | PRD `yt-dlp` / BE `demo` 불일치 | `demo`로 통일, PRD 정정 명시 |
| Twitch URL 흐름 | Step 3에서 암시적 | Step 2(Axis 2)로 끌어올려 프론트/백 동시 수정 |
| test 디렉토리 | 종료 조건에서 암시적 존재 가정 | Section 5.3에서 명시적 생성 |
| STT 테스트 격리 | 미언급 | skipif decorator로 격리 |
| Playwright 인프라 | 미존재 가정만 | dependency 설치 + webServer 설정 명시 |
| 비디오 QA 수치 | 항목만 나열 | 임계치 + 계산식 + 실패 시 조정 포인트 |
| download 검증 | 미언급 | download-verify.spec.ts + ffprobe |
| 상태 격리 | "필요하다" 서술 | conftest.py autouse fixture 코드 제시 |
