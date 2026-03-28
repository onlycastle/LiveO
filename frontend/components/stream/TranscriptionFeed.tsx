"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { TranscriptLine } from "@/lib/types";

interface TranscriptionFeedProps {
  lines: TranscriptLine[];
}

export function TranscriptionFeed({ lines }: TranscriptionFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastLineId = lines[lines.length - 1]?.id;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lastLineId]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-neon-pulse" />
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Live Transcription
          </span>
        </div>
        <span className="text-[10px] font-mono text-muted-foreground/60">
          {lines.length > 0 ? `${lines.length} lines` : "waiting..."}
        </span>
      </div>
      <ScrollArea className="flex-1 px-3">
        <div className="py-2 space-y-1">
          {lines.length === 0 && (
            <div className="text-xs text-muted-foreground/40 text-center py-4">
              Transcription will appear here when audio is detected
            </div>
          )}
          {lines.map((line) => {
            const isLast = line.id === lastLineId;
            const isHighlight = line.isHighlight;

            return (
              <div
                key={line.id}
                className={`flex gap-2 py-1.5 px-2 rounded text-xs transition-colors ${
                  isHighlight
                    ? "bg-neon-lime/6 border-l-2 border-neon-lime"
                    : isLast
                      ? "border-l-2 border-neon-cyan/40 bg-neon-cyan/5"
                      : "hover:bg-secondary/30 border-l-2 border-transparent"
                }`}
              >
                <span className="font-mono text-muted-foreground/50 shrink-0 tabular-nums text-[10px] mt-0.5">
                  {line.timestamp}
                </span>
                <span
                  className={
                    isHighlight
                      ? "text-foreground font-medium"
                      : isLast
                        ? "text-foreground/80"
                        : "text-muted-foreground"
                  }
                >
                  {line.text}
                </span>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
