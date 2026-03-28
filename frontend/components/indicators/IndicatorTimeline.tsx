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

type RowType = "engagement" | "action";

const rowConfig: { type: RowType; label: string; types: IndicatorType[] }[] = [
  {
    type: "engagement",
    label: "CHAT",
    types: ["chat_velocity", "emote_flood", "superchat", "sentiment_shift", "gift_wave"],
  },
  {
    type: "action",
    label: "ACTION",
    types: ["audio_spike", "kill_event", "keyword", "viewer_spike", "clip_burst"],
  },
];

export function IndicatorTimeline() {
  const totalMinutes = 80;
  const totalSeconds = totalMinutes * 60;

  // Time markers every 10 minutes
  const markers = Array.from({ length: 9 }, (_, i) => ({
    label: `${(i * 10).toString().padStart(2, "0")}:00`,
    pos: (i * 10) / totalMinutes,
  }));

  return (
    <div className="px-4 py-2.5">
      {/* Header */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-neon-pulse" />
          <span className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground">
            Indicator Timeline
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[9px] font-mono text-neon-lime tabular-nums">
            62:24
          </span>
          <span className="text-[9px] font-mono text-muted-foreground/50">/</span>
          <span className="text-[9px] font-mono text-muted-foreground tabular-nums">
            80:00
          </span>
        </div>
      </div>

      {/* Time markers */}
      <div className="relative h-3 ml-11">
        {markers.map((m) => (
          <span
            key={m.label}
            className="absolute text-[8px] font-mono text-muted-foreground/50 -translate-x-1/2 tabular-nums"
            style={{ left: `${m.pos * 100}%` }}
          >
            {m.label}
          </span>
        ))}
      </div>

      {/* Heatmap rows */}
      <div className="space-y-1">
        {rowConfig.map((row) => {
          const rowEvents = timelineEvents.filter((e) =>
            row.types.includes(e.type)
          );
          return (
            <div key={row.type} className="flex items-center gap-2">
              <span className="text-[8px] font-mono text-muted-foreground/60 w-9 text-right uppercase shrink-0">
                {row.label}
              </span>
              <div className="flex-1 h-4 relative rounded-sm bg-secondary/20 overflow-hidden">
                {rowEvents.map((e) => (
                  <div
                    key={e.id}
                    className={`absolute top-0 h-full rounded-sm ${typeColorMap[e.type] || "bg-neon-lime"}`}
                    style={{
                      left: `${(e.time / totalSeconds) * 100}%`,
                      width: "1%",
                      opacity: 0.2 + e.intensity * 0.7,
                    }}
                  />
                ))}
                {/* Current position */}
                <div
                  className="absolute top-0 h-full w-0.5 bg-neon-lime/80"
                  style={{ left: "78%" }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* NOW indicator */}
      <div className="relative h-3 ml-11 mt-0.5">
        <div
          className="absolute flex flex-col items-center -translate-x-1/2"
          style={{ left: "78%" }}
        >
          <div className="w-0 h-0 border-l-[3px] border-r-[3px] border-t-[4px] border-transparent border-t-neon-lime" />
          <span className="text-[8px] font-mono text-neon-lime tabular-nums">
            NOW
          </span>
        </div>
      </div>
    </div>
  );
}
