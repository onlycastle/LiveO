#!/usr/bin/env python3
"""
스트리밍 캡처 기능 통합 테스트 스크립트.

사용법:
    python backend/test_stream.py <URL> [--duration 15] [--segment-duration 5]

예시:
    python backend/test_stream.py https://www.twitch.tv/aspen
    python backend/test_stream.py https://www.youtube.com/watch?v=VIDEO_ID --duration 20
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.capture import YtdlpDemoCapture
from backend.events import SegmentReadyEvent, StreamEvent
from backend.pipeline import Pipeline
from backend.ring_buffer import RingBuffer

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_pass(msg: str) -> None:
    print(f"  {GREEN}PASS{RESET}  {msg}")


def log_fail(msg: str) -> None:
    print(f"  {RED}FAIL{RESET}  {msg}")


def log_info(msg: str) -> None:
    print(f"  {YELLOW}INFO{RESET}  {msg}")


def probe_segment(path: str) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            path,
        ],
        capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def run_test(url: str, duration: int, segment_duration: float) -> bool:
    output_dir = tempfile.mkdtemp(prefix="liveo_test_")
    passed = 0
    failed = 0
    total = 0

    def check(condition: bool, msg: str) -> bool:
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            log_pass(msg)
        else:
            failed += 1
            log_fail(msg)
        return condition

    print(f"\n{BOLD}=== LiveO 스트리밍 캡처 테스트 ==={RESET}")
    print(f"  URL:      {url}")
    print(f"  Duration: {duration}s")
    print(f"  Segment:  {segment_duration}s")
    print(f"  Output:   {output_dir}\n")

    # 1. URL 해석
    print(f"{BOLD}[1/5] URL 해석 (yt-dlp --get-url){RESET}")
    cap = YtdlpDemoCapture(url)
    try:
        t0 = time.time()
        stream_url = cap._resolve_stream_url()
        resolve_time = time.time() - t0
        check(len(stream_url) > 0, f"스트림 URL 해석 성공 ({resolve_time:.1f}s)")
        check(stream_url.startswith("http"), f"유효한 HTTP URL")
    except Exception as e:
        check(False, f"URL 해석 실패: {e}")
        shutil.rmtree(output_dir, ignore_errors=True)
        return False

    # 2. 파이프라인 실행
    print(f"\n{BOLD}[2/5] 파이프라인 실행 ({duration}s 캡처){RESET}")
    ring = RingBuffer(max_duration_sec=300)
    pipeline = Pipeline(
        capture=YtdlpDemoCapture(url),
        ring_buffer=ring,
        segment_duration=segment_duration,
        output_dir=output_dir,
    )

    events: list[SegmentReadyEvent] = []
    pipeline.on_segment(lambda e: events.append(e))

    t0 = time.time()
    pipeline.start()
    check(pipeline.capture.is_alive(), "ffmpeg 프로세스 시작됨")

    time.sleep(duration)
    pipeline.stop()
    elapsed = time.time() - t0
    log_info(f"실제 실행 시간: {elapsed:.1f}s")

    # 3. 세그먼트 생성 확인
    print(f"\n{BOLD}[3/5] 세그먼트 생성 확인{RESET}")
    segments = sorted(
        [f for f in os.listdir(output_dir) if f.endswith(".ts")]
    )
    expected_min = max(1, int((duration - 5) / segment_duration))
    check(len(segments) >= 1, f"세그먼트 파일 생성됨 ({len(segments)}개)")
    check(
        len(segments) >= expected_min,
        f"세그먼트 수 >= {expected_min} (실제: {len(segments)})",
    )
    check(len(events) == len(segments), f"이벤트 수 == 세그먼트 수 ({len(events)})")
    check(len(ring) == len(segments), f"RingBuffer 세그먼트 수 일치 ({len(ring)})")

    for evt in events:
        check(evt.event == StreamEvent.SEGMENT_READY, f"이벤트 타입: SEGMENT_READY")
        check(os.path.exists(evt.video_path), f"세그먼트 파일 존재: {os.path.basename(evt.video_path)}")
        check(evt.duration > 0, f"duration > 0 ({evt.duration:.1f}s)")

    # 4. 영상 품질 검증 (ffprobe)
    print(f"\n{BOLD}[4/5] 영상 품질 검증 (ffprobe){RESET}")
    if segments:
        seg_path = os.path.join(output_dir, segments[0])
        seg_size = os.path.getsize(seg_path)
        check(seg_size > 100_000, f"세그먼트 크기 > 100KB ({seg_size / 1024:.0f}KB)")

        probe = probe_segment(seg_path)
        video_streams = [
            s for s in probe.get("streams", []) if s.get("codec_type") == "video"
        ]
        check(len(video_streams) >= 1, "비디오 스트림 존재")

        if video_streams:
            vs = video_streams[0]
            width = int(vs.get("width", 0))
            height = int(vs.get("height", 0))
            codec = vs.get("codec_name", "")
            profile = vs.get("profile", "")
            fps_str = vs.get("r_frame_rate", "0/1")
            fps_num, fps_den = map(int, fps_str.split("/"))
            fps = fps_num / fps_den if fps_den else 0

            check(codec == "h264", f"코덱: H.264 (실제: {codec})")
            check(width >= 1280, f"해상도 width >= 1280 (실제: {width})")
            check(height >= 720, f"해상도 height >= 720 (실제: {height})")
            check(fps >= 30, f"FPS >= 30 (실제: {fps:.0f})")

            is_shorts_ready = width >= 1920 and height >= 1080
            if is_shorts_ready:
                log_pass(f"숏폼 품질 충분: {width}x{height} {fps:.0f}fps {profile}")
            else:
                log_info(f"숏폼 최소 권장(1080p) 미달: {width}x{height}")

    # 5. 정리
    print(f"\n{BOLD}[5/5] 정리{RESET}")
    shutil.rmtree(output_dir, ignore_errors=True)
    check(not os.path.exists(output_dir), "임시 디렉토리 정리 완료")

    # 결과
    print(f"\n{BOLD}=== 결과 ==={RESET}")
    print(f"  통과: {GREEN}{passed}{RESET}/{total}")
    if failed:
        print(f"  실패: {RED}{failed}{RESET}/{total}")
    print()

    return failed == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="LiveO 스트리밍 캡처 테스트")
    parser.add_argument("url", help="YouTube/Twitch 라이브 URL")
    parser.add_argument("--duration", type=int, default=15, help="캡처 시간 (초, 기본: 15)")
    parser.add_argument("--segment-duration", type=float, default=5.0, help="세그먼트 길이 (초, 기본: 5)")
    args = parser.parse_args()

    ok = run_test(args.url, args.duration, args.segment_duration)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
