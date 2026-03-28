"use client";

import { timelineEvents } from "@/lib/mock-data";
import type { IndicatorType } from "@/lib/types";

const typeColorMap: Record<string, string> = {
  chat_velocity: "bg-neon-lime",
  audio_spike: "bg-neon-red",
  superchat: "bg-neon-amber",
  emote_flood: "bg-neon-cyan",
  sentiment_shift: "bg-neon-violet",
  viewer_spike: "bg-neon-cyan",
  kill_event: "bg-neon-red",
  keyword: "bg-neon-lime",
  manual: "bg-white",
  gift_wave: "bg-neon-amber",
  poll_moment: "bg-neon-violet",
  clip_burst: "bg-neon-cyan",
  overlay_alert: "bg-neon-amber",
};

export function IndicatorTimeline() {
  const totalMinutes = 80;

  return (
    <div className="flex items-center gap-3 px-4 py-2">
      {/* Label */}
      <div className="flex items-center gap-1.5 shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-neon-pulse" />
        <span className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground">
          Timeline
        </span>
      </div>

      {/* Single unified bar */}
      <div className="flex-1 h-5 relative rounded bg-secondary/30 overflow-hidden">
        {timelineEvents.map((e) => (
          <div
            key={e.id}
            className={`absolute top-0 h-full rounded-sm ${typeColorMap[e.type] || "bg-neon-lime"}`}
            style={{
              left: `${(e.time / (totalMinutes * 60)) * 100}%`,
              width: "0.8%",
              opacity: 0.15 + e.intensity * 0.7,
            }}
          />
        ))}
        {/* Current position */}
        <div
          className="absolute top-0 h-full w-0.5 bg-neon-lime/80"
          style={{ left: "78%" }}
        />
      </div>

      {/* Time labels */}
      <div className="flex items-center gap-1 shrink-0">
        <span className="text-[9px] font-mono text-neon-lime tabular-nums">
          62:24
        </span>
        <span className="text-[9px] font-mono text-muted-foreground">/</span>
        <span className="text-[9px] font-mono text-muted-foreground tabular-nums">
          80:00
        </span>
      </div>
    </div>
  );
}
