from __future__ import annotations

import argparse
import signal
import sys
import time

from .capture import RTMPStreamCapture, YtdlpDemoCapture
from .events import SegmentReadyEvent
from .pipeline import Pipeline
from .ring_buffer import RingBuffer


def _on_segment(event: SegmentReadyEvent) -> None:
    print(
        f"[segment] {event.video_path} "
        f"({event.timestamp_start:.1f}s ~ {event.timestamp_end:.1f}s, "
        f"{event.duration:.1f}s)",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="LiveO Stream Capture")
    parser.add_argument(
        "--mode", choices=["rtmp", "demo"], default="demo",
        help="Capture mode (default: demo)",
    )
    parser.add_argument(
        "--url", type=str,
        help="YouTube URL (demo mode) or RTMP URL (rtmp mode)",
    )
    parser.add_argument(
        "--segment-duration", type=float, default=5.0,
        help="Segment duration in seconds (default: 5)",
    )
    parser.add_argument(
        "--buffer-duration", type=int, default=300,
        help="Ring buffer max duration in seconds (default: 300)",
    )
    parser.add_argument(
        "--output-dir", type=str, default="",
        help="Output directory for segments",
    )
    args = parser.parse_args()

    if args.mode == "demo":
        if not args.url:
            parser.error("--url is required for demo mode")
        capture = YtdlpDemoCapture(args.url)
    else:
        url = args.url or "rtmp://localhost:1935/live/stream"
        capture = RTMPStreamCapture(url)

    ring_buffer = RingBuffer(max_duration_sec=args.buffer_duration)
    pipeline = Pipeline(
        capture=capture,
        ring_buffer=ring_buffer,
        segment_duration=args.segment_duration,
        output_dir=args.output_dir,
    )
    pipeline.on_segment(_on_segment)

    stop = False

    def _handle_signal(signum: int, frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    print(f"Starting {args.mode} capture...")
    pipeline.start()
    print("Pipeline running. Press Ctrl+C to stop.")

    while not stop and pipeline.capture.is_alive():
        time.sleep(1)

    print("\nStopping pipeline...")
    pipeline.stop()
    print(f"Done. {len(ring_buffer)} segments in buffer.")


def serve() -> None:
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()
    else:
        main()
