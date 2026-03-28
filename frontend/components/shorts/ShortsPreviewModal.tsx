"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";

type CropPosition = "left" | "center" | "right";
type ShortsTemplate = "crop" | "letterbox" | "cam_split";

/**
 * Calculates the crop overlay position as a percentage offset (0-100)
 * for a 9:16 vertical crop within a 16:9 source frame.
 */
function getCropLeftPercent(position: CropPosition): number {
  const cropWidthPercent = ((9 / 16) / (16 / 9)) * 100;
  const maxOffset = 100 - cropWidthPercent;

  switch (position) {
    case "left":
      return 0;
    case "center":
      return maxOffset / 2;
    case "right":
      return maxOffset;
  }
}

const CROP_WIDTH_PERCENT = ((9 / 16) / (16 / 9)) * 100;

/* ─── Template card mini-diagrams ─── */
function CropDiagram() {
  return (
    <svg viewBox="0 0 40 28" className="w-full h-full">
      {/* Dimmed sides */}
      <rect x="0" y="0" width="12" height="28" fill="currentColor" opacity="0.15" />
      <rect x="28" y="0" width="12" height="28" fill="currentColor" opacity="0.15" />
      {/* Center crop zone */}
      <rect x="12" y="0" width="16" height="28" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1.5" opacity="0.8" />
      {/* Arrows */}
      <line x1="18" y1="14" x2="22" y2="14" stroke="currentColor" strokeWidth="1" opacity="0.5" />
    </svg>
  );
}

function LetterboxDiagram() {
  return (
    <svg viewBox="0 0 40 28" className="w-full h-full">
      {/* Top bar */}
      <rect x="0" y="0" width="40" height="7" fill="currentColor" opacity="0.3" />
      {/* Center frame */}
      <rect x="2" y="8" width="36" height="12" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5" />
      <text x="20" y="16" textAnchor="middle" fill="currentColor" fontSize="5" opacity="0.4">16:9</text>
      {/* Bottom bar */}
      <rect x="0" y="21" width="40" height="7" fill="currentColor" opacity="0.3" />
    </svg>
  );
}

function CamSplitDiagram() {
  return (
    <svg viewBox="0 0 40 28" className="w-full h-full">
      {/* Top half — game */}
      <rect x="2" y="1" width="36" height="12" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5" />
      <text x="20" y="9" textAnchor="middle" fill="currentColor" fontSize="4.5" opacity="0.4">GAME</text>
      {/* Divider */}
      <line x1="2" y1="14" x2="38" y2="14" stroke="currentColor" strokeWidth="1" opacity="0.7" />
      {/* Bottom half — cam */}
      <rect x="2" y="15" width="36" height="12" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5" />
      <text x="20" y="23" textAnchor="middle" fill="currentColor" fontSize="4.5" opacity="0.4">CAM</text>
    </svg>
  );
}

function TBDDiagram() {
  return (
    <svg viewBox="0 0 40 28" className="w-full h-full">
      <rect x="2" y="2" width="36" height="24" rx="2" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.2" />
      <text x="20" y="16" textAnchor="middle" fill="currentColor" fontSize="6" opacity="0.25">???</text>
    </svg>
  );
}

const TEMPLATE_OPTIONS: {
  id: ShortsTemplate | "tbd";
  label: string;
  Diagram: React.FC;
  disabled?: boolean;
}[] = [
  { id: "crop", label: "CROP", Diagram: CropDiagram },
  { id: "letterbox", label: "LETTERBOX", Diagram: LetterboxDiagram },
  { id: "cam_split", label: "CAM SPLIT", Diagram: CamSplitDiagram },
  { id: "tbd", label: "COMING SOON", Diagram: TBDDiagram, disabled: true },
];

export function ShortsPreviewModal({
  open,
  onOpenChange,
  shortId,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  shortId: string | null;
}) {
  const [template, setTemplate] = useState<ShortsTemplate>("crop");
  const [cropPosition, setCropPosition] = useState<CropPosition>("center");
  const [isDragging, setIsDragging] = useState(false);
  const [customCropLeft, setCustomCropLeft] = useState<number | null>(null);
  const sourceRef = useRef<HTMLDivElement>(null);

  const activeCropLeft =
    customCropLeft !== null ? customCropLeft : getCropLeftPercent(cropPosition);

  const handlePresetClick = useCallback((pos: CropPosition) => {
    setCropPosition(pos);
    setCustomCropLeft(null);
  }, []);

  // Drag handling for the crop overlay
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const container = sourceRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const containerWidth = rect.width;
      const pct = ((mouseX / containerWidth) * 100) - CROP_WIDTH_PERCENT / 2;
      const clamped = Math.max(0, Math.min(100 - CROP_WIDTH_PERCENT, pct));
      setCustomCropLeft(clamped);
    };

    const handleMouseUp = () => setIsDragging(false);

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  const previewOffsetPercent = -(activeCropLeft / CROP_WIDTH_PERCENT) * 100;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-5xl bg-card border-border p-0 gap-0 overflow-hidden max-h-[85vh] flex flex-col"
        showCloseButton={false}
      >
        {/* ── HEADER ── */}
        <DialogHeader className="px-5 py-3 border-b border-border shrink-0">
          <DialogTitle className="text-sm font-mono font-bold tracking-wider flex items-center gap-2">
            <span className="text-neon-lime neon-text-lime">CROP &amp; PREVIEW</span>
            <span className="text-muted-foreground font-normal">
              — 3연킬 + 채팅 폭발 하이라이트
            </span>
          </DialogTitle>
        </DialogHeader>

        {/* ── THREE-ZONE BODY ── */}
        <div className="flex flex-1 min-h-0 overflow-hidden">

          {/* ═══ ZONE 1: Source Frame (~55%) ═══ */}
          <div className="flex-[55] flex flex-col bg-black/80 border-r border-border min-w-0">
            {/* Source label + crop presets (crop only) */}
            <div className="px-4 py-2 border-b border-border/50 flex items-center justify-between shrink-0">
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                Source Frame — 16:9
              </span>
              {template === "crop" && (
                <div className="flex gap-1">
                  {(["left", "center", "right"] as const).map((pos) => (
                    <button
                      key={pos}
                      onClick={() => handlePresetClick(pos)}
                      className={`h-6 px-2.5 rounded text-[9px] font-mono font-bold uppercase tracking-wider transition-all ${
                        cropPosition === pos && customCropLeft === null
                          ? "border border-neon-cyan text-neon-cyan bg-neon-cyan/10 neon-glow-cyan"
                          : "border border-border text-muted-foreground hover:border-muted-foreground/50 hover:text-foreground"
                      }`}
                    >
                      {pos}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Source frame area */}
            <div className="flex-1 flex items-center justify-center p-4 min-h-0">
              <div
                ref={sourceRef}
                className="relative w-full aspect-video rounded-lg overflow-hidden bg-gradient-to-br from-zinc-800 via-zinc-900 to-zinc-950 border border-border/30 select-none"
              >
                {/* Mock source content — game scene placeholder */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-zinc-800/50 via-zinc-900 to-zinc-950" />
                  <div className="relative grid grid-cols-3 gap-4 opacity-20 pointer-events-none">
                    {[...Array(6)].map((_, i) => (
                      <div
                        key={i}
                        className="w-12 h-12 rounded bg-zinc-700/50 border border-zinc-600/30"
                      />
                    ))}
                  </div>
                  <span className="absolute text-[10px] font-mono text-zinc-600 bottom-2 right-3">
                    STREAM FRAME
                  </span>
                </div>

                {/* ── CROP template overlay ── */}
                {template === "crop" && (
                  <>
                    {/* Dimmed areas outside crop */}
                    <div
                      className="absolute inset-y-0 left-0 bg-black/60 pointer-events-none transition-all duration-150"
                      style={{ width: `${activeCropLeft}%` }}
                    />
                    <div
                      className="absolute inset-y-0 right-0 bg-black/60 pointer-events-none transition-all duration-150"
                      style={{ width: `${100 - activeCropLeft - CROP_WIDTH_PERCENT}%` }}
                    />

                    {/* Crop overlay — draggable */}
                    <div
                      onMouseDown={handleMouseDown}
                      className={`absolute inset-y-0 border-2 border-dashed border-neon-cyan/70 transition-all duration-150 z-10 ${
                        isDragging ? "cursor-grabbing" : "cursor-grab"
                      }`}
                      style={{
                        left: `${activeCropLeft}%`,
                        width: `${CROP_WIDTH_PERCENT}%`,
                      }}
                    >
                      <div className="absolute -top-0 left-1/2 -translate-x-1/2 bg-neon-cyan/90 text-black text-[8px] font-mono font-bold px-2 py-0.5 rounded-b tracking-wider">
                        9:16 CROP
                      </div>
                      <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-neon-cyan" />
                      <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-neon-cyan" />
                      <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-neon-cyan" />
                      <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-neon-cyan" />
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-0.5 opacity-50">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-neon-cyan">
                          <path d="M4 8H12M8 4V12M4 8L6 6M4 8L6 10M12 8L10 6M12 8L10 10M8 4L6 6M8 4L10 6M8 12L6 10M8 12L10 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                        <span className="text-[7px] font-mono text-neon-cyan tracking-wider">DRAG</span>
                      </div>
                    </div>
                  </>
                )}

                {/* ── LETTERBOX template overlay ── */}
                {template === "letterbox" && (
                  <>
                    {/* Top letterbox bar */}
                    <div className="absolute top-0 inset-x-0 h-[18%] bg-black/70 flex items-center justify-center z-10 border-b border-neon-cyan/20">
                      <span className="text-[9px] font-mono text-white/60 tracking-wider">
                        3연킬 미쳤다!!!
                      </span>
                    </div>
                    {/* Bottom letterbox bar */}
                    <div className="absolute bottom-0 inset-x-0 h-[18%] bg-black/70 flex items-center justify-center z-10 border-t border-neon-cyan/20">
                      <span className="text-[8px] font-mono text-white/40 tracking-wider">
                        @streamer_name
                      </span>
                    </div>
                    {/* Full frame indicator */}
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
                      <span className="text-[8px] font-mono text-neon-cyan/50 bg-black/40 px-2 py-1 rounded tracking-wider">
                        FULL FRAME — NO CROP
                      </span>
                    </div>
                  </>
                )}

                {/* ── CAM SPLIT template overlay ── */}
                {template === "cam_split" && (
                  <>
                    {/* Top half label */}
                    <div className="absolute top-2 left-1/2 -translate-x-1/2 z-10">
                      <span className="text-[8px] font-mono text-neon-cyan/60 bg-black/40 px-2 py-0.5 rounded tracking-wider">
                        GAME FOOTAGE
                      </span>
                    </div>
                    {/* Horizontal split line */}
                    <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 z-10 flex items-center gap-2 px-3">
                      <div className="flex-1 h-[2px] bg-neon-cyan/60" />
                      <span className="text-[7px] font-mono text-neon-cyan/80 tracking-wider shrink-0">SPLIT</span>
                      <div className="flex-1 h-[2px] bg-neon-cyan/60" />
                    </div>
                    {/* Bottom half — cam placeholder */}
                    <div className="absolute bottom-0 inset-x-0 h-1/2 bg-black/50 flex items-center justify-center z-[5]">
                      <div className="flex flex-col items-center gap-1 opacity-50">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-neon-cyan">
                          <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
                          <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
                          <circle cx="12" cy="12" r="1" fill="currentColor" />
                        </svg>
                        <span className="text-[8px] font-mono text-neon-cyan/60 tracking-wider">CAM FEED</span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Template selector — below source frame */}
            <div className="px-4 pb-3 pt-1 border-t border-border/50 shrink-0">
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2 block">
                Template
              </span>
              <div className="flex gap-2">
                {TEMPLATE_OPTIONS.map(({ id, label, Diagram, disabled }) => {
                  const isActive = template === id;
                  return (
                    <button
                      key={id}
                      disabled={disabled}
                      onClick={() => !disabled && setTemplate(id as ShortsTemplate)}
                      className={`flex flex-col items-center gap-1.5 rounded-md px-2 py-2 w-20 transition-all ${
                        disabled
                          ? "border border-border/30 bg-secondary/10 opacity-40 cursor-not-allowed"
                          : isActive
                          ? "border-2 border-neon-cyan bg-secondary/40 neon-glow-cyan"
                          : "border border-border bg-secondary/20 hover:border-muted-foreground/40 cursor-pointer"
                      }`}
                    >
                      <div className={`w-10 h-7 ${isActive ? "text-neon-cyan" : "text-muted-foreground"}`}>
                        <Diagram />
                      </div>
                      <span className={`text-[8px] font-mono font-bold tracking-wider ${
                        disabled ? "text-muted-foreground/40" : isActive ? "text-neon-cyan" : "text-muted-foreground"
                      }`}>
                        {label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* ═══ ZONE 2: Phone Preview (~120px) ═══ */}
          <div className="w-[140px] flex flex-col shrink-0 border-r border-border bg-black/60">
            <div className="px-3 py-2 border-b border-border/50 shrink-0">
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                Preview
              </span>
            </div>

            <div className="flex-1 flex items-center justify-center p-3 min-h-0">
              <div className="w-full aspect-[9/16] rounded-xl border-2 border-border bg-gradient-to-b from-zinc-900 to-zinc-950 relative overflow-hidden">
                {/* Notch */}
                <div className="absolute top-1.5 left-1/2 -translate-x-1/2 w-10 h-1 rounded-full bg-zinc-700 z-10" />

                {/* ── CROP preview ── */}
                {template === "crop" && (
                  <div className="absolute inset-0 overflow-hidden">
                    <div
                      className="absolute inset-y-0 transition-all duration-150"
                      style={{
                        width: `${(100 / CROP_WIDTH_PERCENT) * 100}%`,
                        left: `${previewOffsetPercent}%`,
                      }}
                    >
                      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-zinc-800/50 via-zinc-900 to-zinc-950" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="grid grid-cols-3 gap-2 opacity-20 pointer-events-none">
                          {[...Array(6)].map((_, i) => (
                            <div key={i} className="w-4 h-4 rounded bg-zinc-700/50 border border-zinc-600/30" />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── LETTERBOX preview ── */}
                {template === "letterbox" && (
                  <div className="absolute inset-0 flex flex-col">
                    {/* Top black bar with title */}
                    <div className="h-[20%] bg-black flex items-center justify-center px-1">
                      <span className="text-[6px] font-mono text-white/70 text-center leading-tight">
                        3연킬 미쳤다!!!
                      </span>
                    </div>
                    {/* Center — full 16:9 content scaled to fit */}
                    <div className="flex-1 relative overflow-hidden">
                      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-zinc-800/50 via-zinc-900 to-zinc-950" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="grid grid-cols-3 gap-1 opacity-20 pointer-events-none">
                          {[...Array(6)].map((_, i) => (
                            <div key={i} className="w-3 h-3 rounded bg-zinc-700/50 border border-zinc-600/30" />
                          ))}
                        </div>
                      </div>
                      <span className="absolute bottom-0.5 right-1 text-[5px] font-mono text-zinc-600">16:9</span>
                    </div>
                    {/* Bottom black bar with streamer name */}
                    <div className="h-[20%] bg-black flex items-center justify-center px-1">
                      <span className="text-[6px] font-mono text-white/50">@streamer_name</span>
                    </div>
                  </div>
                )}

                {/* ── CAM SPLIT preview ── */}
                {template === "cam_split" && (
                  <div className="absolute inset-0 flex flex-col">
                    {/* Top half — game footage */}
                    <div className="flex-1 relative overflow-hidden">
                      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-zinc-800/50 via-zinc-900 to-zinc-950" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="grid grid-cols-3 gap-1 opacity-20 pointer-events-none">
                          {[...Array(6)].map((_, i) => (
                            <div key={i} className="w-3 h-3 rounded bg-zinc-700/50 border border-zinc-600/30" />
                          ))}
                        </div>
                      </div>
                      <span className="absolute top-2 left-1/2 -translate-x-1/2 text-[5px] font-mono text-zinc-500">GAME</span>
                    </div>
                    {/* Neon divider */}
                    <div className="h-[2px] bg-neon-cyan/60 shrink-0" />
                    {/* Bottom half — cam placeholder */}
                    <div className="flex-1 bg-gradient-to-b from-zinc-900 to-zinc-950 flex items-center justify-center relative">
                      <div className="flex flex-col items-center gap-0.5 opacity-40">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-neon-cyan">
                          <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" strokeWidth="2" />
                          <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
                        </svg>
                        <span className="text-[5px] font-mono text-neon-cyan/50">CAM</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Play button overlay */}
                <div className="absolute inset-0 flex items-center justify-center z-10">
                  <div className="w-8 h-8 rounded-full bg-neon-lime/10 border border-neon-lime/30 flex items-center justify-center">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" className="text-neon-lime ml-0.5">
                      <path d="M4 3L12 8L4 13V3Z" />
                    </svg>
                  </div>
                </div>

                {/* Bottom gradient + info */}
                <div className="absolute bottom-0 inset-x-0 h-12 bg-gradient-to-t from-black/80 to-transparent z-10" />
                <div className="absolute bottom-2 inset-x-2 z-10">
                  <p className="text-[7px] text-white font-medium mb-0.5 line-clamp-2">
                    3연킬 + 채팅 폭발 하이라이트
                  </p>
                  <p className="text-[6px] text-white/60">@streamer_name</p>
                </div>

                {/* Template / crop indicator */}
                <div className="absolute top-3 right-1.5 z-10">
                  <span className="text-[5px] font-mono text-neon-cyan/70 bg-black/60 px-1 py-0.5 rounded uppercase">
                    {template === "crop"
                      ? customCropLeft !== null
                        ? "custom"
                        : cropPosition
                      : template.replace("_", " ")}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ═══ ZONE 3: Controls (~240px) ═══ */}
          <div className="w-[240px] flex flex-col shrink-0 min-h-0">
            <div className="px-4 py-2 border-b border-border/50 shrink-0">
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                Controls
              </span>
            </div>

            <div className="overflow-y-auto flex-1 min-h-0 px-4 py-3 flex flex-col gap-4">
              {/* Trim */}
              <div>
                <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2 block">
                  Trim Range
                </label>
                <Slider defaultValue={[10, 90]} min={0} max={100} step={1} className="mb-1" />
                <div className="flex justify-between">
                  <span className="text-[9px] font-mono text-muted-foreground tabular-nums">01:23:50</span>
                  <span className="text-[9px] font-mono text-neon-lime tabular-nums">0:30</span>
                  <span className="text-[9px] font-mono text-muted-foreground tabular-nums">01:24:20</span>
                </div>
              </div>

              {/* Caption */}
              <div>
                <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2 block">
                  Caption
                </label>
                <textarea
                  defaultValue="3연킬 미쳤다!!! 🔥"
                  className="w-full h-16 rounded-md bg-secondary/60 border border-border px-2 py-1.5 text-xs text-foreground resize-none focus:outline-none focus:ring-1 focus:ring-neon-lime/50"
                />
              </div>

              {/* Tags */}
              <div>
                <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2 block">
                  Detected Indicators
                </label>
                <div className="flex flex-wrap gap-1">
                  <Badge variant="outline" className="text-[9px] font-mono border-neon-red/30 text-neon-red bg-neon-red/10">
                    Kill Event
                  </Badge>
                  <Badge variant="outline" className="text-[9px] font-mono border-neon-lime/30 text-neon-lime bg-neon-lime/10">
                    Chat
                  </Badge>
                  <Badge variant="outline" className="text-[9px] font-mono border-neon-red/30 text-neon-red bg-neon-red/10">
                    Audio
                  </Badge>
                </div>
              </div>

              {/* Export Format */}
              <div>
                <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2 block">
                  Export Format
                </label>
                <div className="flex gap-2">
                  <button className="flex-1 h-7 rounded text-[10px] font-mono font-bold border-2 border-neon-lime text-neon-lime bg-neon-lime/10">
                    MP4
                  </button>
                  <button className="flex-1 h-7 rounded text-[10px] font-mono font-bold border border-border text-muted-foreground hover:border-muted-foreground/50">
                    WEBM
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── FOOTER — sticky full-width ── */}
        <div className="border-t border-border px-5 py-3 flex items-center gap-3 shrink-0 bg-card">
          <Button className="flex-1 h-9 font-mono text-xs font-bold tracking-wider bg-neon-lime text-black hover:bg-neon-lime/80 neon-glow-lime">
            GENERATE SHORT
          </Button>
          <Button
            variant="ghost"
            className="h-9 px-6 font-mono text-[10px] text-muted-foreground"
            onClick={() => onOpenChange(false)}
          >
            CANCEL
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
