from apps.live_server.events import StreamEvent, SegmentReadyEvent


class TestStreamEvent:
    def test_enum_values(self):
        assert StreamEvent.STREAM_STARTED.value == "stream_started"
        assert StreamEvent.SEGMENT_READY.value == "segment_ready"
        assert StreamEvent.AUDIO_READY.value == "audio_ready"
        assert StreamEvent.STREAM_ERROR.value == "stream_error"

    def test_enum_members_count(self):
        assert len(StreamEvent) == 4

    def test_enum_from_value(self):
        assert StreamEvent("stream_started") is StreamEvent.STREAM_STARTED


class TestSegmentReadyEvent:
    def test_creation(self):
        evt = SegmentReadyEvent(
            event=StreamEvent.SEGMENT_READY,
            video_path="/tmp/seg_001.ts",
            audio_path="/tmp/seg_001.wav",
            timestamp_start=0.0,
            timestamp_end=5.0,
            duration=5.0,
        )
        assert evt.event == StreamEvent.SEGMENT_READY
        assert evt.video_path == "/tmp/seg_001.ts"
        assert evt.audio_path == "/tmp/seg_001.wav"
        assert evt.duration == 5.0

    def test_equality(self):
        kwargs = dict(
            event=StreamEvent.SEGMENT_READY,
            video_path="/tmp/a.ts",
            audio_path="/tmp/a.wav",
            timestamp_start=0.0,
            timestamp_end=1.0,
            duration=1.0,
        )
        assert SegmentReadyEvent(**kwargs) == SegmentReadyEvent(**kwargs)

    def test_timestamp_range(self):
        evt = SegmentReadyEvent(
            event=StreamEvent.SEGMENT_READY,
            video_path="v.ts",
            audio_path="a.wav",
            timestamp_start=10.0,
            timestamp_end=15.0,
            duration=5.0,
        )
        assert evt.timestamp_end - evt.timestamp_start == evt.duration
