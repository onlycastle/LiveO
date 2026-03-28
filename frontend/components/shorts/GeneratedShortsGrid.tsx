"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { generatedShorts } from "@/lib/mock-data";
import type { GeneratedShort } from "@/lib/types";

function ShortsViewModal({
  open,
  onOpenChange,
  short,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  short: GeneratedShort | null;
}) {
  if (!short) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg bg-card border-border p-0 overflow-hidden max-h-[85vh] flex flex-col">
        <DialogHeader className="px-5 py-3 border-b border-border shrink-0">
          <DialogTitle className="text-sm font-mono font-bold tracking-wider flex items-center gap-2">
            <span className="text-neon-lime">GENERATED SHORT</span>
            <span className="text-muted-foreground font-normal truncate">
              — {short.title}
            </span>
          </DialogTitle>
        </DialogHeader>

        {/* 9:16 Preview */}
        <div className="flex-1 flex items-center justify-center bg-black/50 p-6">
          <div className="w-[220px] aspect-[9/16] rounded-xl border border-border bg-gradient-to-b from-zinc-900 to-zinc-950 relative overflow-hidden">
            {/* Phone notch */}
            <div className="absolute top-2 left-1/2 -translate-x-1/2 w-12 h-1 rounded-full bg-zinc-700" />

            {/* Content */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="w-14 h-14 rounded-full bg-neon-lime/10 border border-neon-lime/30 flex items-center justify-center mx-auto mb-3">
                  <svg width="24" height="24" viewBox="0 0 16 16" fill="currentColor" className="text-neon-lime ml-1">
                    <path d="M4 3L12 8L4 13V3Z" />
                  </svg>
                </div>
                <span className="text-xs font-mono text-muted-foreground">{short.duration}</span>
              </div>
            </div>

            {/* Bottom overlay */}
            <div className="absolute bottom-0 inset-x-0 h-24 bg-gradient-to-t from-black/80 to-transparent" />
            <div className="absolute bottom-4 inset-x-4">
              <p className="text-sm text-white font-medium mb-1">{short.title}</p>
              <p className="text-[10px] text-white/50 font-mono">@streamer_name</p>
            </div>

            {/* Side engagement icons */}
            <div className="absolute right-3 bottom-28 flex flex-col items-center gap-4">
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" /></svg>
                </div>
                <span className="text-[8px] text-white/60 font-mono">2.4K</span>
              </div>
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                </div>
                <span className="text-[8px] text-white/60 font-mono">128</span>
              </div>
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" /><polyline points="16 6 12 2 8 6" /><line x1="12" y1="2" x2="12" y2="15" /></svg>
                </div>
                <span className="text-[8px] text-white/60 font-mono">Share</span>
              </div>
            </div>
          </div>
        </div>

        {/* Info + Actions */}
        <div className="shrink-0 px-5 py-4 border-t border-border space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">{short.title}</p>
              <p className="text-[10px] font-mono text-muted-foreground mt-0.5">
                {short.duration} · {short.createdAt} · {short.indicators.join(", ")}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button className="flex-1 h-9 font-mono text-xs font-bold tracking-wider bg-neon-lime text-black hover:bg-neon-lime/80">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              DOWNLOAD MP4
            </Button>
            <Button
              variant="outline"
              className="h-9 px-4 font-mono text-xs"
              onClick={() => onOpenChange(false)}
            >
              CLOSE
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function GeneratedShortsGrid() {
  const [viewShort, setViewShort] = useState<GeneratedShort | null>(null);

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-lime" />
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Generated Shorts
          </span>
        </div>
        <span className="text-[10px] font-mono text-neon-lime tabular-nums">
          {generatedShorts.length} READY
        </span>
      </div>
      <div className="flex gap-3 p-3 overflow-x-auto scrollbar-none">
        {generatedShorts.map((short) => (
          <div
            key={short.id}
            onClick={() => setViewShort(short)}
            className="group relative shrink-0 w-28 rounded-lg border border-border bg-secondary/30 overflow-hidden hover:border-neon-lime/40 transition-all cursor-pointer"
          >
            <div className="aspect-[9/14] bg-gradient-to-b from-secondary to-background relative">
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5">
                <div className="w-8 h-8 rounded-full bg-neon-lime/10 border border-neon-lime/30 flex items-center justify-center group-hover:bg-neon-lime/20 transition-colors">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" className="text-neon-lime ml-0.5">
                    <path d="M4 3L12 8L4 13V3Z" />
                  </svg>
                </div>
                <span className="text-[8px] font-mono text-muted-foreground tabular-nums">
                  {short.duration}
                </span>
              </div>
              <div className="absolute bottom-0 inset-x-0 h-12 bg-gradient-to-t from-black/80 to-transparent" />
              <div className="absolute bottom-0 inset-x-0 p-1.5">
                <p className="text-[9px] font-medium text-white leading-tight line-clamp-2 break-words">
                  {short.title}
                </p>
              </div>
            </div>
            <div className="px-1.5 py-1 flex items-center justify-between min-w-0">
              <span className="text-[8px] font-mono text-muted-foreground truncate">
                {short.createdAt}
              </span>
            </div>
          </div>
        ))}
      </div>

      <ShortsViewModal
        open={viewShort !== null}
        onOpenChange={(v) => !v && setViewShort(null)}
        short={viewShort}
      />
    </div>
  );
}
