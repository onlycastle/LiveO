"use client";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { ShortsCandidate, IndicatorType } from "@/lib/types";
import { resolveBackendUrl } from "@/lib/utils";

const indicatorLabels: Record<IndicatorType, string> = {
  manual: "Manual", chat_velocity: "Chat", superchat: "SuperChat",
  audio_spike: "Audio", emote_flood: "Emote", sentiment_shift: "Sentiment",
  viewer_spike: "Viewers", clip_burst: "Clips", kill_event: "Kill",
  keyword: "Keyword", gift_wave: "Gifts", poll_moment: "Poll", overlay_alert: "Alert",
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

const statusConfig: Record<ShortsCandidate["status"], { label: string; color: string; border: string }> = {
  pending: { label: "NEW", color: "text-neon-lime", border: "border-neon-lime/30" },
  confirmed: { label: "CONFIRMED", color: "text-neon-cyan", border: "border-neon-cyan/30" },
  generating: { label: "GENERATING", color: "text-neon-amber", border: "border-neon-amber/30" },
  dismissed: { label: "DISMISSED", color: "text-muted-foreground", border: "border-muted-foreground/20" },
  done: { label: "DONE", color: "text-neon-lime", border: "border-neon-lime/30" },
};

/* Confidence ring */
function ConfidenceRing({ value }: { value: number }) {
  const radius = 14;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const color = value >= 80 ? "stroke-neon-lime" : value >= 60 ? "stroke-neon-cyan" : "stroke-neon-amber";

  return (
    <div className="relative shrink-0">
      <svg width="36" height="36" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r={radius} fill="none" stroke="currentColor" className="text-secondary" strokeWidth="3" />
        <circle cx="18" cy="18" r={radius} fill="none" className={color} strokeWidth="3" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset} transform="rotate(-90 18 18)" />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-mono text-[9px] font-bold text-foreground tabular-nums">
        {value}
      </span>
    </div>
  );
}

export function ShortsCandidateCard({
  candidate,
  onPreview,
  onConfirm,
  onDismiss,
  onUndo,
}: {
  candidate: ShortsCandidate;
  onPreview: (id: string) => void;
  onConfirm: (id: string) => void;
  onDismiss: (id: string) => void;
  onUndo: (id: string) => void;
}) {
  const isManual = candidate.isManual;
  const isDismissed = candidate.status === "dismissed";
  const config = statusConfig[candidate.status];

  if (isDismissed) {
    return (
      <div data-testid={`candidate-card-${candidate.id}`} className="shrink-0 w-48 h-full rounded-lg border border-muted-foreground/15 bg-secondary/5 flex flex-col items-center justify-center gap-1 opacity-40">
        <span className="text-[9px] font-mono text-muted-foreground uppercase">DISMISSED</span>
        <span className="text-[10px] text-muted-foreground/60 text-center px-3 line-clamp-2">{candidate.title}</span>
        <button data-testid={`candidate-undo-${candidate.id}`} className="text-[9px] font-mono text-neon-cyan/50 hover:text-neon-cyan mt-1" onClick={() => onUndo(candidate.id)}>UNDO</button>
      </div>
    );
  }

  const cardBorder = isManual ? "border-white/30" : config.border;

  return (
    <div data-testid={`candidate-card-${candidate.id}`} className={`shrink-0 w-56 h-full rounded-lg border ${cardBorder} bg-card/60 flex flex-col overflow-hidden`}>
      {/* Top: 9:16 thumbnail preview */}
      <div className="relative aspect-[9/12] bg-gradient-to-b from-secondary to-background shrink-0">
        {candidate.thumbnailUrl && (
          <img src={resolveBackendUrl(candidate.thumbnailUrl) ?? candidate.thumbnailUrl} alt="" className="absolute inset-0 w-full h-full object-cover" />
        )}
        {/* Status badge */}
        <div className="absolute top-2 left-2 z-10">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase tracking-wider bg-black/60 backdrop-blur-sm ${config.color}`}>
            {isManual ? "📌 MANUAL" : config.label}
          </span>
        </div>

        {/* Confidence ring */}
        <div className="absolute top-2 right-2 z-10">
          <ConfidenceRing value={candidate.confidence} />
        </div>

        {/* Center play icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-10 h-10 rounded-full bg-black/30 border border-white/20 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="white" className="ml-0.5">
              <path d="M4 3L12 8L4 13V3Z" />
            </svg>
          </div>
        </div>

        {/* Bottom overlay with time */}
        <div className="absolute bottom-0 inset-x-0 h-12 bg-gradient-to-t from-black/80 to-transparent" />
        <div className="absolute bottom-2 inset-x-2 flex items-center justify-between z-10">
          <span className="text-[9px] font-mono text-white/70 tabular-nums">{candidate.startTime}</span>
          <span className="text-[9px] font-mono text-white/50">({candidate.duration})</span>
          <span className="text-[9px] font-mono text-white/70 tabular-nums">{candidate.endTime}</span>
        </div>

        {/* Generating progress overlay */}
        {candidate.status === "generating" && candidate.progress != null && (
          <div className="absolute bottom-0 inset-x-0 z-20">
            <Progress value={candidate.progress} className="h-1 rounded-none" />
          </div>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 flex flex-col p-3 gap-2 min-h-0">
        {/* Title */}
        <h4 className="text-sm font-semibold text-foreground leading-snug line-clamp-2">
          {candidate.title}
        </h4>

        {/* Indicator tags */}
        <div className="flex flex-wrap gap-1">
          {candidate.indicators.map((ind) => (
            <span key={ind} className={`inline-flex items-center px-1.5 py-0.5 rounded text-[8px] font-mono border ${indicatorColorMap[ind] || "bg-secondary text-foreground"}`}>
              {indicatorLabels[ind]}
            </span>
          ))}
        </div>

        {/* Manual transcript context */}
        {isManual && candidate.capturedTranscript && (
          <p className="text-[9px] text-muted-foreground leading-relaxed line-clamp-2 italic">
            &ldquo;{candidate.capturedTranscript}&rdquo;
          </p>
        )}

        {/* Generating status */}
        {candidate.status === "generating" && candidate.progress != null && (
          <span className="text-[9px] font-mono text-neon-amber">
            {candidate.progress}% · ~{Math.max(1, Math.round((100 - candidate.progress) / 10))}s
          </span>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        {candidate.status === "pending" && (
          <div className="flex gap-1.5">
            <Button data-testid={`candidate-confirm-${candidate.id}`} size="sm" className="flex-1 h-7 text-[9px] font-mono font-bold tracking-wider bg-neon-lime text-black hover:bg-neon-lime/80" onClick={() => onConfirm(candidate.id)}>
              CONFIRM
            </Button>
            <Button data-testid={`candidate-skip-${candidate.id}`} size="sm" variant="ghost" className="h-7 px-2 text-[9px] font-mono text-muted-foreground hover:text-destructive" onClick={() => onDismiss(candidate.id)}>
              SKIP
            </Button>
          </div>
        )}
        {candidate.status === "confirmed" && (
          <Button data-testid={`candidate-preview-${candidate.id}`} size="sm" variant="outline" onClick={() => onPreview(candidate.id)}
            className="w-full h-7 text-[9px] font-mono font-bold tracking-wider border-neon-cyan/30 text-neon-cyan hover:bg-neon-cyan/10">
            PREVIEW
          </Button>
        )}
      </div>
    </div>
  );
}
