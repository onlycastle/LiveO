"use client";

import { StreamEmbed } from "@/components/stream/StreamEmbed";
import { IndicatorDashboard } from "@/components/indicators/IndicatorDashboard";
import { TranscriptionFeed } from "@/components/stream/TranscriptionFeed";
import { ManualCaptureButton } from "@/components/indicators/ManualCaptureButton";
import type { TranscriptLine, Indicator } from "@/lib/types";

interface LeftPanelProps {
  onCapture: (holdDurationMs: number) => void;
  transcriptLines: TranscriptLine[];
  indicators: Indicator[];
  streamUrl?: string;
}

export function LeftPanel({ onCapture, transcriptLines, indicators, streamUrl }: LeftPanelProps) {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Stream — fixed, never clipped */}
      <div className="shrink-0 p-3 pb-0">
        <StreamEmbed streamUrl={streamUrl} />
      </div>

      {/* Indicators — fixed */}
      <div className="shrink-0 border-t border-border mt-3">
        <IndicatorDashboard indicators={indicators} />
      </div>

      {/* Capture button — fixed */}
      <div data-testid="manual-capture-button" className="shrink-0 border-t border-border">
        <ManualCaptureButton onCapture={onCapture} />
      </div>

      {/* Transcription — fills remaining, scrolls internally */}
      <div data-testid="transcript-feed" className="flex-1 min-h-[120px] border-t border-border overflow-hidden">
        <TranscriptionFeed lines={transcriptLines} />
      </div>
    </div>
  );
}
