"use client";

import { indicators } from "@/lib/mock-data";

const barColorMap: Record<string, string> = {
  "neon-lime": "bg-neon-lime",
  "neon-cyan": "bg-neon-cyan",
  "neon-red": "bg-neon-red",
  "neon-amber": "bg-neon-amber",
  "neon-violet": "bg-neon-violet",
};

export function IndicatorDashboard() {
  const activeCount = indicators.filter((i) => i.active).length;

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-lime animate-neon-pulse" />
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Indicators
          </span>
        </div>
        <span className="text-[10px] font-mono text-muted-foreground tabular-nums">
          {activeCount}/{indicators.length} ACTIVE
        </span>
      </div>
      <div className="grid grid-cols-2 gap-1.5 p-3">
        {indicators.map((ind) => (
          <div
            key={ind.id}
            className={`flex items-center gap-2 px-2.5 py-2 rounded-md border transition-all ${
              ind.active
                ? "border-border bg-secondary/30"
                : "border-border bg-secondary/10 opacity-35"
            }`}
          >
            <span className="text-sm shrink-0">{ind.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-muted-foreground truncate">
                  {ind.label}
                </span>
                <span
                  className={`text-[10px] font-mono font-bold tabular-nums ${
                    ind.active && ind.value > 75
                      ? "text-neon-lime"
                      : "text-muted-foreground"
                  }`}
                >
                  {ind.value}
                </span>
              </div>
              <div className="h-1 rounded-full bg-secondary overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    barColorMap[ind.color] || "bg-neon-lime"
                  }`}
                  style={{ width: `${ind.value}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
