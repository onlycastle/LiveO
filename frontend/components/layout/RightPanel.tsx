"use client";

import { useState, useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";

import { ShortsCandidateCard } from "@/components/shorts/ShortsCandidateCard";
import { GeneratedShortsGrid } from "@/components/shorts/GeneratedShortsGrid";
import type { ShortsCandidate } from "@/lib/types";

export function RightPanel({
  candidates,
  onPreview,
}: {
  candidates: ShortsCandidate[];
  onPreview: (id: string) => void;
}) {
  const [headerFlash, setHeaderFlash] = useState(false);
  const prevCountRef = useRef(candidates.length);

  useEffect(() => {
    if (candidates.length > prevCountRef.current) {
      setHeaderFlash(true);
      const timer = setTimeout(() => setHeaderFlash(false), 1200);
      prevCountRef.current = candidates.length;
      return () => clearTimeout(timer);
    }
    prevCountRef.current = candidates.length;
  }, [candidates.length]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Shorts Candidates */}
      <div className="flex-1 min-h-0 border-b border-border">
        <div
          key={headerFlash ? "flash" : "idle"}
          className={`flex items-center justify-between px-4 py-2 border-b border-border ${headerFlash ? "animate-header-flash" : ""}`}
        >
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-neon-amber animate-neon-pulse" />
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
              Shorts Candidates
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono text-neon-lime tabular-nums">
              {candidates.filter((c) => c.status === "pending").length} PENDING
            </span>
            <span className="text-[10px] font-mono text-neon-amber tabular-nums">
              {candidates.filter((c) => c.status === "generating").length} GENERATING
            </span>
          </div>
        </div>
        <ScrollArea className="h-[calc(100%-36px)]">
          <div className="p-4 space-y-3">
            {candidates.map((c) => (
              <ShortsCandidateCard
                key={c.id}
                candidate={c}
                onPreview={onPreview}
              />
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Generated Shorts */}
      <div className="shrink-0">
        <GeneratedShortsGrid />
      </div>
    </div>
  );
}
