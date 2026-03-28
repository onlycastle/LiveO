"use client";

import { StreamEmbed } from "@/components/stream/StreamEmbed";
import { IndicatorDashboard } from "@/components/indicators/IndicatorDashboard";
import { TranscriptionFeed } from "@/components/stream/TranscriptionFeed";
import { ManualCaptureButton } from "@/components/indicators/ManualCaptureButton";

export function LeftPanel({ onCapture }: { onCapture: (holdDurationMs: number) => void }) {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Stream — fixed, never clipped */}
      <div className="shrink-0 p-3 pb-0">
        <StreamEmbed />
      </div>

      {/* Indicators — fixed */}
      <div className="shrink-0 border-t border-border mt-3">
        <IndicatorDashboard />
      </div>

      {/* Capture button — fixed */}
      <div className="shrink-0 border-t border-border">
        <ManualCaptureButton onCapture={onCapture} />
      </div>

      {/* Transcription — fills remaining, scrolls internally */}
      <div className="flex-1 min-h-[120px] border-t border-border overflow-hidden">
        <TranscriptionFeed />
      </div>
    </div>
  );
}
