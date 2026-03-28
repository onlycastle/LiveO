"use client";

import { useState, useCallback } from "react";
import { LandingScreen } from "@/components/landing/LandingScreen";
import { Header } from "@/components/layout/Header";
import { LeftPanel } from "@/components/layout/LeftPanel";
import { RightPanel } from "@/components/layout/RightPanel";
import { SettingsModal } from "@/components/modals/SettingsModal";
import { ShortsPreviewModal } from "@/components/shorts/ShortsPreviewModal";
import { shortsCandidates as initialCandidates, transcriptLines } from "@/lib/mock-data";
import type { ShortsCandidate } from "@/lib/types";

export default function Home() {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<ShortsCandidate[]>(initialCandidates);

  const handleManualCapture = useCallback(() => {
    // Find the latest highlight transcript line as anchor point
    const now = transcriptLines[transcriptLines.length - 3]; // simulate "current" position
    const startIdx = Math.max(0, transcriptLines.length - 6);
    const endIdx = Math.min(transcriptLines.length - 1, transcriptLines.length - 1);
    const startLine = transcriptLines[startIdx];
    const endLine = transcriptLines[endIdx];

    // Build captured transcript snippet
    const capturedText = transcriptLines
      .slice(startIdx, endIdx + 1)
      .map((l) => l.text)
      .join(" ");

    const newCandidate: ShortsCandidate = {
      id: `manual-${Date.now()}`,
      startTime: startLine.timestamp,
      endTime: endLine.timestamp,
      duration: "0:30",
      thumbnailUrl: "",
      title: `📌 수동 캡처 — "${now.text.slice(0, 20)}..."`,
      indicators: ["manual"],
      confidence: 100,
      status: "pending",
      isManual: true,
      capturedTranscript: capturedText,
    };

    setCandidates((prev) => [newCandidate, ...prev]);
  }, []);

  if (!streamUrl) {
    return <LandingScreen onConnect={setStreamUrl} />;
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header onSettingsOpen={() => setSettingsOpen(true)} />

      <div className="flex-1 flex min-h-0">
        <div className="w-[40%] min-w-[480px] border-r border-border">
          <LeftPanel onCapture={handleManualCapture} />
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
