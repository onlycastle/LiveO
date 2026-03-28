"use client";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { ShortsCandidate, IndicatorType } from "@/lib/types";

const indicatorLabels: Record<IndicatorType, string> = {
  manual: "Manual",
  chat_velocity: "Chat",
  superchat: "SuperChat",
  audio_spike: "Audio",
  emote_flood: "Emote",
  sentiment_shift: "Sentiment",
  viewer_spike: "Viewers",
  clip_burst: "Clips",
  kill_event: "Kill",
  keyword: "Keyword",
  gift_wave: "Gifts",
  poll_moment: "Poll",
  overlay_alert: "Alert",
};

const indicatorColorMap: Record<string, string> = {
  chat_velocity: "bg-neon-lime/15 text-neon-lime border-neon-lime/20",
  audio_spike: "bg-neon-red/15 text-neon-red border-neon-red/20",
  superchat: "bg-neon-amber/15 text-neon-amber border-neon-amber/20",
  emote_flood: "bg-neon-cyan/15 text-neon-cyan border-neon-cyan/20",
  sentiment_shift: "bg-neon-violet/15 text-neon-violet border-neon-violet/20",
  kill_event: "bg-neon-red/15 text-neon-red border-neon-red/20",
  keyword: "bg-neon-lime/15 text-neon-lime border-neon-lime/20",
  manual: "bg-white/10 text-white border-white/20",
  viewer_spike: "bg-neon-cyan/15 text-neon-cyan border-neon-cyan/20",
  clip_burst: "bg-neon-cyan/15 text-neon-cyan border-neon-cyan/20",
  gift_wave: "bg-neon-amber/15 text-neon-amber border-neon-amber/20",
  poll_moment: "bg-neon-violet/15 text-neon-violet border-neon-violet/20",
  overlay_alert: "bg-neon-amber/15 text-neon-amber border-neon-amber/20",
};

/* ── Status → left-edge strip color ── */
const statusStripColor: Record<ShortsCandidate["status"], string> = {
  pending: "bg-neon-lime",
  confirmed: "bg-neon-cyan",
  generating: "bg-neon-amber",
  dismissed: "bg-muted-foreground/40",
  done: "bg-neon-lime",
};

/* ── Status badge config ── */
const statusConfig: Record<
  ShortsCandidate["status"],
  { label: string; color: string; bgColor: string }
> = {
  pending: {
    label: "NEW",
    color: "text-neon-lime",
    bgColor: "bg-neon-lime/10 border-neon-lime/25",
  },
  confirmed: {
    label: "CONFIRMED",
    color: "text-neon-cyan",
    bgColor: "bg-neon-cyan/10 border-neon-cyan/25",
  },
  generating: {
    label: "GENERATING",
    color: "text-neon-amber",
    bgColor: "bg-neon-amber/10 border-neon-amber/25",
  },
  dismissed: {
    label: "DISMISSED",
    color: "text-muted-foreground",
    bgColor: "bg-secondary/30 border-muted-foreground/20",
  },
  done: {
    label: "DONE",
    color: "text-neon-lime",
    bgColor: "bg-neon-lime/10 border-neon-lime/25",
  },
};

/* ── Confidence Ring (SVG donut) ── */
function ConfidenceRing({
  value,
  size = 32,
  strokeWidth = 3,
  className = "",
}: {
  value: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  // Color based on confidence level
  const ringColor =
    value >= 80
      ? "stroke-neon-lime"
      : value >= 60
        ? "stroke-neon-cyan"
        : value >= 40
          ? "stroke-neon-amber"
          : "stroke-neon-red";

  return (
    <div className={`relative shrink-0 ${className}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          className="text-secondary"
          strokeWidth={strokeWidth}
        />
        {/* Value arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className={ringColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-mono text-[8px] font-bold text-foreground tabular-nums">
        {value}
      </span>
    </div>
  );
}

/* ── Thumbnail with 9:16 crop overlay ── */
function ThumbnailPreview() {
  return (
    <div className="w-16 h-10 rounded bg-secondary/60 border border-border shrink-0 overflow-hidden relative">
      {/* 16:9 source frame */}
      <div className="w-full h-full bg-gradient-to-br from-secondary to-background" />
      {/* 9:16 crop overlay — centered vertical strip */}
      <div className="absolute inset-0 flex items-center justify-center">
        {/* Dim the outer areas */}
        <div className="absolute inset-0 bg-black/40" />
        {/* Bright 9:16 crop zone */}
        <div className="relative w-[22%] h-full border border-neon-cyan/50 bg-transparent z-10">
          <div className="absolute inset-0 bg-neon-cyan/5" />
          <span className="absolute inset-0 flex items-center justify-center text-[6px] font-mono text-neon-cyan/80 font-bold">
            9:16
          </span>
        </div>
      </div>
    </div>
  );
}

/* ── Pin icon for manual captures ── */
function PinIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
    >
      <path d="M9.828 4.172l2 2a1 1 0 010 1.414L9.95 9.464a1 1 0 01-.708.293H7.5L6 12.5 4.5 14l-.354-.354L6.793 11H5.243a1 1 0 01-.707-.293L2.414 8.586a1 1 0 010-1.414l2.122-2.122A4 4 0 019.828 4.172z" />
    </svg>
  );
}

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */

export function ShortsCandidateCard({
  candidate,
  onPreview,
}: {
  candidate: ShortsCandidate;
  onPreview: (id: string) => void;
}) {
  const isManual = candidate.isManual;
  const isDismissed = candidate.status === "dismissed";
  const config = statusConfig[candidate.status];

  /* ── Dismissed: collapsed single-line view ── */
  if (isDismissed) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-muted-foreground/15 bg-secondary/10 px-3 py-1.5 group">
        {/* Left strip — thin vertical bar */}
        <div className="w-0.5 h-4 rounded-full bg-muted-foreground/30 shrink-0" />

        <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground/60">
          DISMISSED
        </span>
        <span className="text-xs text-muted-foreground/50 truncate flex-1 font-sans">
          {candidate.title}
        </span>
        <span className="text-[9px] font-mono text-muted-foreground/40 tabular-nums shrink-0">
          {candidate.startTime}
        </span>
        <span className="text-[9px] font-mono text-muted-foreground/40 tabular-nums shrink-0">
          {candidate.confidence}%
        </span>
      </div>
    );
  }

  /* ── Manual capture overrides ── */
  const manualLabel = isManual ? "MANUAL" : config.label;
  const manualBadgeBg = isManual
    ? "bg-white/10 border-white/30"
    : config.bgColor;
  const manualBadgeColor = isManual ? "text-white" : config.color;
  const cardBorder = isManual
    ? "border-white/30 ring-1 ring-white/10"
    : "border-border/60";
  const stripColor = isManual
    ? "bg-white"
    : statusStripColor[candidate.status];

  return (
    <div
      className={`relative rounded-lg border overflow-hidden transition-all ${cardBorder} bg-card/60`}
    >
      {/* ── Colored left-edge strip ── */}
      <div
        className={`absolute left-0 top-0 bottom-0 w-[3px] ${stripColor} ${
          candidate.status === "generating" ? "animate-neon-pulse" : ""
        }`}
      />

      {/* ── Card body ── */}
      <div className="pl-3.5 pr-3 py-3">
        {/* Row 1: Status badge + confidence ring + thumbnail */}
        <div className="flex items-start gap-2.5 mb-2">
          {/* Left: badge + title block */}
          <div className="flex-1 min-w-0">
            {/* Status badge — larger & more prominent */}
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono font-bold uppercase tracking-wider ${manualBadgeBg} ${manualBadgeColor}`}
              >
                {isManual && <PinIcon className="opacity-80" />}
                {manualLabel}
              </span>

              {/* Manual: extra bright "MANUAL" call-out */}
              {isManual && candidate.status === "pending" && (
                <span className="text-[8px] font-mono font-bold text-white/50 tracking-widest">
                  PINNED
                </span>
              )}
            </div>

            {/* Title — more prominent */}
            <h4 className="text-sm font-sans font-semibold text-foreground leading-snug line-clamp-2">
              {candidate.title}
            </h4>
          </div>

          {/* Right: confidence ring + thumbnail */}
          <div className="flex items-center gap-2 shrink-0">
            <ConfidenceRing value={candidate.confidence} />
            <ThumbnailPreview />
          </div>
        </div>

        {/* Row 2: Time range — subtle */}
        <div className="flex items-center gap-1.5 mb-2">
          <span className="text-[9px] font-mono text-muted-foreground/60 tabular-nums">
            {candidate.startTime}
          </span>
          <div className="flex-1 h-px bg-border/50" />
          <span className="text-[9px] font-mono text-muted-foreground/60 tabular-nums">
            {candidate.endTime}
          </span>
          <span className="text-[9px] font-mono text-foreground/40">
            ({candidate.duration})
          </span>
        </div>

        {/* Row 3: Indicator tags */}
        <div className="flex flex-wrap gap-1 mb-2.5">
          {candidate.indicators.map((ind) => (
            <span
              key={ind}
              className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono border ${
                indicatorColorMap[ind] || "bg-secondary text-foreground"
              }`}
            >
              {indicatorLabels[ind]}
            </span>
          ))}
        </div>

        {/* Manual capture transcript context */}
        {isManual && candidate.capturedTranscript && (
          <div className="mb-2.5 px-2 py-1.5 rounded bg-white/[0.03] border border-white/10">
            <span className="text-[9px] font-mono text-muted-foreground/70 block mb-0.5">
              TRANSCRIPT CONTEXT
            </span>
            <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-2 font-sans">
              &ldquo;{candidate.capturedTranscript}&rdquo;
            </p>
          </div>
        )}

        {/* Generating progress */}
        {candidate.status === "generating" && candidate.progress != null && (
          <div className="mb-2.5">
            <Progress value={candidate.progress} className="h-1" />
            <span className="text-[9px] font-mono text-neon-amber mt-0.5 block">
              {candidate.progress}% PROCESSING...
            </span>
          </div>
        )}

        {/* Actions */}
        {candidate.status === "pending" && (
          <div className="flex gap-2">
            <Button
              size="sm"
              className="flex-1 h-7 text-[10px] font-mono font-bold tracking-wider bg-neon-lime text-black hover:bg-neon-lime/80"
            >
              CONFIRM
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="flex-1 h-7 text-[10px] font-mono font-bold tracking-wider text-muted-foreground hover:text-destructive"
            >
              DISMISS
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onPreview(candidate.id)}
              className="h-7 px-2 text-[10px] font-mono"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M4 3L12 8L4 13V3Z" />
              </svg>
            </Button>
          </div>
        )}
        {candidate.status === "confirmed" && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onPreview(candidate.id)}
            className="w-full h-7 text-[10px] font-mono font-bold tracking-wider border-neon-cyan/30 text-neon-cyan hover:bg-neon-cyan/10"
          >
            PREVIEW
          </Button>
        )}
      </div>
    </div>
  );
}
