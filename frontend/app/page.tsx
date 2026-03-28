"use client";

import { useState, useCallback } from "react";
import { LandingScreen } from "@/components/landing/LandingScreen";
import { DebugConsole } from "@/components/debug/DebugConsole";
import { Header } from "@/components/layout/Header";
import { LeftPanel } from "@/components/layout/LeftPanel";
import { RightPanel } from "@/components/layout/RightPanel";
import { SettingsModal } from "@/components/modals/SettingsModal";
import { ShortsPreviewModal } from "@/components/shorts/ShortsPreviewModal";
import { useLiveO } from "@/lib/use-liveo";
import type { ShortsCandidate } from "@/lib/types";

function formatElapsedTime(totalSeconds: number) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
}

export default function Home() {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewId, setPreviewId] = useState<string | null>(null);

  const {
    candidates,
    generatedShorts,
    transcriptLines,
    indicators,
    streamStatus,
    wsConnected,
    debugLogs,
    confirmCandidate,
    dismissCandidate,
    undoCandidate,
    createCandidate,
    generateShorts,
  } = useLiveO();

  const handleManualCapture = useCallback((holdDurationMs: number) => {
    // Calculate how many transcript lines the hold covers (~3s per line)
    const holdSeconds = holdDurationMs / 1000;
    const linesForHold = Math.max(2, Math.ceil(holdSeconds / 3));

    // If no transcript lines available yet, create a minimal candidate
    if (transcriptLines.length === 0) {
      const totalDuration = Math.min(60, Math.round(holdSeconds + 10));
      const endSeconds = Math.max(0, Math.floor(streamStatus.elapsed));
      const startSeconds = Math.max(0, endSeconds - totalDuration);
      const startTime = formatElapsedTime(startSeconds);
      const endTime = formatElapsedTime(endSeconds);
      const durationStr = totalDuration >= 60 ? "1:00" : `0:${totalDuration.toString().padStart(2, "0")}`;

      const draftCandidate: Omit<ShortsCandidate, "id" | "progress"> = {
        startTime,
        endTime,
        duration: durationStr,
        thumbnailUrl: "",
        title: `Manual Capture at ${endTime}`,
        indicators: ["manual"],
        confidence: 100,
        status: "pending",
        isManual: true,
      };
      void createCandidate(draftCandidate).catch((error) => {
        console.error("Failed to create manual candidate", error);
      });
      return;
    }

    // Anchor at "current" position + extend by hold duration + buffer
    const bufferLines = 2; // extra context before/after
    const endIdx = transcriptLines.length - 1;
    const startIdx = Math.max(0, endIdx - linesForHold - bufferLines);
    const startLine = transcriptLines[startIdx];
    const endLine = transcriptLines[endIdx];
    const anchorLine = transcriptLines[Math.max(0, endIdx - Math.floor(linesForHold / 2))];

    // Build captured transcript snippet
    const capturedText = transcriptLines
      .slice(startIdx, endIdx + 1)
      .map((l) => l.text)
      .join(" ");

    // Duration based on hold time + buffer
    const totalDuration = Math.min(60, Math.round(holdSeconds + 10));
    const durationStr = totalDuration >= 60 ? "1:00" : `0:${totalDuration.toString().padStart(2, "0")}`;

    // When start/end transcript lines share the same timestamp, fall back to
    // elapsed-based window so the backend always gets a non-zero clip range.
    let startTime = startLine.timestamp;
    let endTime = endLine.timestamp;
    if (startTime === endTime) {
      const endSeconds = Math.max(0, Math.floor(streamStatus.elapsed));
      const startSeconds = Math.max(0, endSeconds - totalDuration);
      startTime = formatElapsedTime(startSeconds);
      endTime = formatElapsedTime(endSeconds);
    }

    const newCandidate: Omit<ShortsCandidate, "id" | "progress"> = {
      startTime,
      endTime,
      duration: durationStr,
      thumbnailUrl: "",
      title: `Manual Capture -- "${anchorLine.text.slice(0, 24)}..."`,
      indicators: ["manual"],
      confidence: 100,
      status: "pending",
      isManual: true,
      capturedTranscript: capturedText,
    };

    void createCandidate(newCandidate).catch((error) => {
      console.error("Failed to create manual candidate", error);
    });
  }, [createCandidate, streamStatus.elapsed, transcriptLines]);

  if (!streamUrl) {
    return <LandingScreen onConnect={setStreamUrl} />;
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header
        onSettingsOpen={() => setSettingsOpen(true)}
        streamUrl={streamUrl}
        isLive={streamStatus.isLive}
        wsConnected={wsConnected}
        elapsed={Math.max(0, Math.floor(streamStatus.elapsed))}
        shortsCount={generatedShorts.length}
        queueCount={candidates.filter((candidate) => !["dismissed", "done"].includes(candidate.status)).length}
      />

      <div className="flex-1 flex min-h-0">
        <div className="w-[40%] min-w-[480px] border-r border-border">
          <LeftPanel
            onCapture={handleManualCapture}
            transcriptLines={transcriptLines}
            indicators={indicators}
            streamUrl={streamUrl ?? undefined}
          />
        </div>
        <div className="flex-1 min-w-[640px]">
          <RightPanel
            candidates={candidates}
            generatedShorts={generatedShorts}
            onPreview={(id) => {
              setPreviewId(id);
              setPreviewOpen(true);
            }}
            onConfirm={confirmCandidate}
            onDismiss={dismissCandidate}
            onUndo={undoCandidate}
          />
        </div>
      </div>

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
      <ShortsPreviewModal
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        shortId={previewId}
        onGenerate={generateShorts}
      />
      <DebugConsole
        logs={debugLogs}
        wsConnected={wsConnected}
        streamStatus={streamStatus}
        streamUrl={streamUrl}
        candidateCount={candidates.length}
        generatedCount={generatedShorts.length}
      />
    </div>
  );
}
