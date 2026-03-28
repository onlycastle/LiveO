"use client";

import { useState, useCallback } from "react";
import { LandingScreen } from "@/components/landing/LandingScreen";
import { Header } from "@/components/layout/Header";
import { LeftPanel } from "@/components/layout/LeftPanel";
import { RightPanel } from "@/components/layout/RightPanel";
import { SettingsModal } from "@/components/modals/SettingsModal";
import { ShortsPreviewModal } from "@/components/shorts/ShortsPreviewModal";
import { useWebSocket } from "@/lib/use-websocket";
import { shortsCandidates as initialCandidates } from "@/lib/mock-data";
import type { ShortsCandidate, TranscriptLine } from "@/lib/types";

export default function Home() {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<ShortsCandidate[]>(initialCandidates);
  const [transcriptLines, setTranscriptLines] = useState<TranscriptLine[]>([]);

  const handleWsMessage = useCallback((type: string, data: Record<string, unknown>) => {
    if (type === "transcript_update") {
      const line: TranscriptLine = {
        id: data.id as string,
        timestamp: data.timestamp as string,
        text: data.text as string,
        isHighlight: data.isHighlight as boolean | undefined,
      };
      setTranscriptLines((prev) => [...prev.slice(-199), line]);
    }
  }, []);

  useWebSocket(handleWsMessage);

  const handleManualCapture = useCallback((holdDurationMs: number) => {
    const holdSeconds = holdDurationMs / 1000;
    const linesForHold = Math.max(2, Math.ceil(holdSeconds / 3));
    const bufferLines = 2;
    const endIdx = transcriptLines.length - 1;
    const startIdx = Math.max(0, endIdx - linesForHold - bufferLines);
    const startLine = transcriptLines[startIdx];
    const endLine = transcriptLines[endIdx];
    const anchorLine = transcriptLines[Math.max(0, endIdx - Math.floor(linesForHold / 2))];

    if (!startLine || !endLine || !anchorLine) return;

    const capturedText = transcriptLines
      .slice(startIdx, endIdx + 1)
      .map((l) => l.text)
      .join(" ");

    const totalDuration = Math.min(60, Math.round(holdSeconds + 10));
    const durationStr = totalDuration >= 60 ? "1:00" : `0:${totalDuration.toString().padStart(2, "0")}`;

    const newCandidate: ShortsCandidate = {
      id: `manual-${Date.now()}`,
      startTime: startLine.timestamp,
      endTime: endLine.timestamp,
      duration: durationStr,
      thumbnailUrl: "",
      title: `Manual capture — "${anchorLine.text.slice(0, 24)}..."`,
      indicators: ["manual"],
      confidence: 100,
      status: "pending",
      isManual: true,
      capturedTranscript: capturedText,
    };

    setCandidates((prev) => [newCandidate, ...prev]);
  }, [transcriptLines]);

  if (!streamUrl) {
    return <LandingScreen onConnect={setStreamUrl} />;
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header onSettingsOpen={() => setSettingsOpen(true)} />

      <div className="flex-1 flex min-h-0">
        <div className="w-[40%] min-w-[480px] border-r border-border">
          <LeftPanel onCapture={handleManualCapture} transcriptLines={transcriptLines} />
        </div>
        <div className="flex-1 min-w-[640px]">
          <RightPanel
            candidates={candidates}
            onPreview={(id) => {
              setPreviewId(id);
              setPreviewOpen(true);
            }}
          />
        </div>
      </div>

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
      <ShortsPreviewModal
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        shortId={previewId}
      />
    </div>
  );
}
