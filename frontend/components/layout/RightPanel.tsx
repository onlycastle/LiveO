"use client";

import { useState, useEffect, useRef } from "react";
import { ShortsCandidateCard } from "@/components/shorts/ShortsCandidateCard";
import { GeneratedShortsGrid } from "@/components/shorts/GeneratedShortsGrid";
import type { ShortsCandidate, GeneratedShort } from "@/lib/types";

export function RightPanel({
  candidates,
  generatedShorts,
  onPreview,
  onConfirm,
  onDismiss,
  onUndo,
}: {
  candidates: ShortsCandidate[];
  generatedShorts: GeneratedShort[];
  onPreview: (id: string) => void;
  onConfirm: (id: string) => void;
  onDismiss: (id: string) => void;
  onUndo: (id: string) => void;
}) {
  const [headerFlash, setHeaderFlash] = useState(false);
  const prevCountRef = useRef(candidates.length);

  useEffect(() => {
    if (candidates.length > prevCountRef.current) {
      const frame = window.requestAnimationFrame(() => setHeaderFlash(true));
      const timer = window.setTimeout(() => setHeaderFlash(false), 1200);
      prevCountRef.current = candidates.length;
      return () => {
        window.cancelAnimationFrame(frame);
        window.clearTimeout(timer);
      };
    }
    prevCountRef.current = candidates.length;
  }, [candidates.length]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Shorts Candidates — horizontal scroll */}
      <div className="flex-1 min-h-0">
        <div
          key={headerFlash ? "flash" : "idle"}
          className={`flex items-center justify-between px-4 py-2 border-b border-border ${headerFlash ? "animate-header-flash" : ""}`}
        >
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-neon-lime animate-neon-pulse" />
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
              Shorts Candidates
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono text-neon-lime tabular-nums">
              {candidates.filter((c) => c.status === "pending").length} PENDING
            </span>
            <span className="text-[10px] font-mono text-muted-foreground tabular-nums">
              {candidates.filter((c) => c.status === "generating").length} GENERATING
            </span>
          </div>
        </div>
        <div className="h-[calc(100%-36px)] overflow-x-auto overflow-y-hidden scrollbar-none">
          <div className="flex gap-3 p-4 h-full">
            {candidates.map((c) => (
              <ShortsCandidateCard
                key={c.id}
                candidate={c}
                onPreview={onPreview}
                onConfirm={onConfirm}
                onDismiss={onDismiss}
                onUndo={onUndo}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Generated Shorts */}
      <div className="shrink-0 border-t border-border">
        <GeneratedShortsGrid generatedShorts={generatedShorts} />
      </div>
    </div>
  );
}
