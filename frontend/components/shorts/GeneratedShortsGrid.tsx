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
import type { GeneratedShort, ShortsTemplate } from "@/lib/types";

const templateLabels: Record<ShortsTemplate, string> = {
  blur_fill: "BLUR FILL",
  letterbox: "LETTERBOX",
  cam_split: "CAM SPLIT",
};

const templateDescriptions: Record<ShortsTemplate, string> = {
  blur_fill: "Original center + blur bg",
  letterbox: "Original + black bars + caption",
  cam_split: "Game top + cam bottom",
};

/* Template visual preview inside the 9:16 card */
function TemplatePreview({ template, caption }: { template: ShortsTemplate; caption?: string }) {
  if (template === "blur_fill") {
    return (
      <div className="absolute inset-0 flex flex-col">
        {/* Blurred background */}
        <div className="absolute inset-0 bg-gradient-to-b from-zinc-700 via-zinc-800 to-zinc-700 opacity-40" />
        <div className="absolute inset-0 backdrop-blur-sm" />
        {/* Centered 16:9 content */}
        <div className="flex-1 flex items-center justify-center relative">
          <div className="w-[90%] aspect-video bg-gradient-to-br from-zinc-700 to-zinc-900 rounded border border-zinc-600/30" />
        </div>
      </div>
    );
  }

  if (template === "letterbox") {
    return (
      <div className="absolute inset-0 flex flex-col">
        {/* Top black bar */}
        <div className="h-[28%] bg-black flex items-end justify-center pb-1">
          <span className="text-[6px] font-mono text-white/30">LIVEO</span>
        </div>
        {/* 16:9 content */}
        <div className="flex-1 bg-gradient-to-br from-zinc-700 to-zinc-900" />
        {/* Bottom black bar with caption */}
        <div className="h-[28%] bg-black flex items-start justify-center pt-2 px-2">
          <span className="text-[7px] text-white/80 text-center leading-tight line-clamp-2">
            {caption || "Caption here..."}
          </span>
        </div>
      </div>
    );
  }

  // cam_split
  return (
    <div className="absolute inset-0 flex flex-col">
      {/* Game footage top half */}
      <div className="flex-1 bg-gradient-to-br from-zinc-700 to-zinc-900 relative">
        <span className="absolute bottom-1 left-1.5 text-[6px] font-mono text-white/30">GAME</span>
      </div>
      {/* Divider */}
      <div className="h-px bg-neon-cyan/40" />
      {/* Cam bottom half */}
      <div className="flex-1 bg-gradient-to-br from-zinc-800 to-zinc-950 relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-8 h-8 rounded-full bg-zinc-700/50 border border-zinc-600/30" />
        </div>
        <span className="absolute bottom-1 left-1.5 text-[6px] font-mono text-white/30">CAM</span>
      </div>
    </div>
  );
}

/* View modal for a single generated short */
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
      <DialogContent className="max-w-md bg-card border-border p-0 overflow-hidden max-h-[85vh] flex flex-col">
        <DialogHeader className="px-5 py-3 border-b border-border shrink-0">
          <DialogTitle className="text-sm font-mono font-bold tracking-wider flex items-center gap-2">
            <span className="text-neon-lime">{templateLabels[short.template]}</span>
            <span className="text-muted-foreground font-normal truncate">
              — {short.title}
            </span>
          </DialogTitle>
        </DialogHeader>

        {/* 9:16 Preview */}
        <div className="flex-1 flex items-center justify-center bg-black/50 p-6">
          <div className="w-[200px] aspect-[9/16] rounded-xl border border-border bg-zinc-950 relative overflow-hidden">
            <TemplatePreview template={short.template} caption={short.caption} />
            {/* Play button overlay */}
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="w-12 h-12 rounded-full bg-black/40 border border-white/20 flex items-center justify-center">
                <svg width="20" height="20" viewBox="0 0 16 16" fill="white" className="ml-0.5">
                  <path d="M4 3L12 8L4 13V3Z" />
                </svg>
              </div>
            </div>
            {/* Bottom info */}
            <div className="absolute bottom-0 inset-x-0 h-16 bg-gradient-to-t from-black/80 to-transparent z-10" />
            <div className="absolute bottom-3 inset-x-3 z-10">
              <p className="text-[10px] text-white font-medium">{short.title}</p>
              <p className="text-[8px] text-white/50 font-mono mt-0.5">{short.duration} · {templateLabels[short.template]}</p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="shrink-0 px-5 py-4 border-t border-border flex gap-2">
          <Button className="flex-1 h-9 font-mono text-xs font-bold tracking-wider bg-neon-lime text-black hover:bg-neon-lime/80">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            DOWNLOAD
          </Button>
          <Button variant="outline" className="h-9 px-4 font-mono text-xs" onClick={() => onOpenChange(false)}>
            CLOSE
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* Bundle: group of 3 templates from same highlight */
function ShortBundle({ shorts }: { shorts: GeneratedShort[] }) {
  const [viewShort, setViewShort] = useState<GeneratedShort | null>(null);

  // Recommended = blur_fill (most TikTok-friendly)
  const recommended = shorts.find((s) => s.template === "blur_fill") || shorts[0];
  const others = shorts.filter((s) => s.id !== recommended.id);

  return (
    <div className="flex gap-2">
      {/* Recommended — larger card */}
      <div
        onClick={() => setViewShort(recommended)}
        className="relative shrink-0 w-32 rounded-lg border border-neon-lime/30 bg-secondary/30 overflow-hidden hover:border-neon-lime/50 transition-all cursor-pointer"
      >
        {/* "RECOMMENDED" badge */}
        <div className="absolute top-1.5 left-1.5 z-10 px-1.5 py-0.5 rounded bg-neon-lime/90 text-[7px] font-mono font-bold text-black tracking-wider">
          REC
        </div>
        <div className="aspect-[9/14] relative">
          <TemplatePreview template={recommended.template} caption={recommended.caption} />
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="w-8 h-8 rounded-full bg-black/30 border border-white/20 flex items-center justify-center">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="white" className="ml-0.5">
                <path d="M4 3L12 8L4 13V3Z" />
              </svg>
            </div>
          </div>
          <div className="absolute bottom-0 inset-x-0 h-10 bg-gradient-to-t from-black/80 to-transparent z-10" />
          <div className="absolute bottom-0 inset-x-0 p-1.5 z-10">
            <p className="text-[8px] font-mono text-neon-lime">{templateLabels[recommended.template]}</p>
          </div>
        </div>
        <div className="px-1.5 py-1">
          <p className="text-[8px] font-medium text-foreground truncate">{recommended.title}</p>
          <p className="text-[7px] font-mono text-muted-foreground">{recommended.duration} · {recommended.createdAt}</p>
        </div>
      </div>

      {/* Other templates — smaller cards */}
      <div className="flex flex-col gap-2">
        {others.map((s) => (
          <div
            key={s.id}
            onClick={() => setViewShort(s)}
            className="relative shrink-0 w-20 rounded-lg border border-border bg-secondary/30 overflow-hidden hover:border-muted-foreground/50 transition-all cursor-pointer"
          >
            <div className="aspect-[9/14] relative">
              <TemplatePreview template={s.template} caption={s.caption} />
              <div className="absolute bottom-0 inset-x-0 h-8 bg-gradient-to-t from-black/80 to-transparent z-10" />
              <div className="absolute bottom-0 inset-x-0 p-1 z-10">
                <p className="text-[7px] font-mono text-muted-foreground">{templateLabels[s.template]}</p>
              </div>
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

export function GeneratedShortsGrid() {
  // Group shorts into bundles of 3 (by title)
  const bundleMap = new Map<string, GeneratedShort[]>();
  for (const s of generatedShorts) {
    const key = s.title;
    if (!bundleMap.has(key)) bundleMap.set(key, []);
    bundleMap.get(key)!.push(s);
  }
  const bundles = Array.from(bundleMap.values());

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
          {bundles.length} {bundles.length === 1 ? "BUNDLE" : "BUNDLES"}
        </span>
      </div>
      <div className="flex gap-4 p-3 overflow-x-auto scrollbar-none">
        {bundles.map((bundle, i) => (
          <ShortBundle key={i} shorts={bundle} />
        ))}
      </div>
    </div>
  );
}
