"use client";

import { StreamEmbed } from "@/components/stream/StreamEmbed";
import { IndicatorDashboard } from "@/components/indicators/IndicatorDashboard";
import { TranscriptionFeed } from "@/components/stream/TranscriptionFeed";
import { ManualCaptureButton } from "@/components/indicators/ManualCaptureButton";

export function LeftPanel({ onCapture }: { onCapture: () => void }) {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Fixed top: Stream + Indicators + Capture */}
      <div className="shrink-0 overflow-y-auto">
        <div className="p-3 pb-0">
          <StreamEmbed />
        </div>
        <div className="border-t border-border mt-3">
          <IndicatorDashboard />
        </div>
        <div className="border-t border-border">
          <ManualCaptureButton onCapture={onCapture} />
        </div>
      </div>

      {/* Transcription fills remaining space */}
      <div className="flex-1 min-h-0 border-t border-border">
        <TranscriptionFeed />
      </div>
    </div>
  );
}
