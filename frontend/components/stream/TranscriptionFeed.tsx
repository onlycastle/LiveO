"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { transcriptLines } from "@/lib/mock-data";

function WaveformIcon() {
  return (
    <div className="flex items-end gap-[1.5px] w-[10px] h-3 shrink-0 overflow-hidden">
      <div
        className="w-[2px] rounded-full bg-neon-cyan"
        style={{ height: "40%", animation: "waveform-bar-1 0.8s ease-in-out infinite" }}
      />
      <div
        className="w-[2px] rounded-full bg-neon-cyan"
        style={{ height: "70%", animation: "waveform-bar-2 0.6s ease-in-out infinite" }}
      />
      <div
        className="w-[2px] rounded-full bg-neon-cyan"
        style={{ height: "50%", animation: "waveform-bar-3 0.7s ease-in-out infinite" }}
      />
    </div>
  );
}

export function TranscriptionFeed() {
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastLineId = transcriptLines[transcriptLines.length - 1]?.id;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-border">
        <div className="flex items-center gap-2">
          <WaveformIcon />
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Live Transcription
          </span>
        </div>
        <span className="text-[10px] font-mono text-muted-foreground/70">
          WHISPER v3
        </span>
      </div>
      <ScrollArea className="flex-1 px-3">
        <div className="py-2 space-y-1">
          {transcriptLines.map((line) => {
            const isLast = line.id === lastLineId;
            const isHighlight = line.isHighlight;

            return (
              <div
                key={line.id}
                className={`flex gap-2 py-1.5 px-2 rounded text-xs transition-all duration-300 ${
                  isHighlight
                    ? "animate-highlight-pulse border-l-2 border-neon-lime"
                    : isLast
                      ? "border-l-2 animate-speaking-glow bg-neon-cyan/5"
                      : "hover:bg-secondary/40 border-l-2 border-transparent"
                }`}
              >
                <span className="font-mono text-muted-foreground/60 shrink-0 tabular-nums text-[10px] mt-0.5">
                  {line.timestamp}
                </span>
                <div className="flex items-start gap-1.5 flex-1 min-w-0">
                  {isLast && (
                    <div className="mt-0.5 shrink-0">
                      <WaveformIcon />
                    </div>
                  )}
                  <span
                    className={
                      isHighlight
                        ? "text-foreground font-medium"
                        : isLast
                          ? "text-neon-cyan/90 font-medium"
                          : "text-muted-foreground"
                    }
                  >
                    {line.text}
                  </span>
                </div>
                {isHighlight && (
                  <span className="shrink-0 text-[8px] font-mono text-neon-lime/70 uppercase tracking-wider mt-0.5">
                    HIT
                  </span>
                )}
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
