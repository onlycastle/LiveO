"use client";

import { indicators } from "@/lib/mock-data";

const colorMap: Record<string, string> = {
  "neon-lime": "bg-neon-lime",
  "neon-cyan": "bg-neon-cyan",
  "neon-red": "bg-neon-red",
  "neon-amber": "bg-neon-amber",
  "neon-violet": "bg-neon-violet",
};

const glowMap: Record<string, string> = {
  "neon-lime": "neon-glow-lime",
  "neon-cyan": "neon-glow-cyan",
  "neon-red": "neon-glow-red",
  "neon-amber": "neon-glow-amber",
  "neon-violet": "neon-glow-violet",
};

const dotGlowMap: Record<string, string> = {
  "neon-lime": "shadow-[0_0_6px_oklch(0.795_0.184_128.25/0.6)]",
  "neon-cyan": "shadow-[0_0_6px_oklch(0.777_0.152_199.57/0.6)]",
  "neon-red": "shadow-[0_0_6px_oklch(0.637_0.237_15.163/0.6)]",
  "neon-amber": "shadow-[0_0_6px_oklch(0.795_0.184_84.429/0.6)]",
  "neon-violet": "shadow-[0_0_6px_oklch(0.702_0.183_293.54/0.6)]",
};

function TrendArrow({ value, active }: { value: number; active: boolean }) {
  if (!active) return null;
  const isHigh = value > 75;
  const isMid = value > 40;
  return (
    <span
      className={`text-[8px] ml-0.5 inline-block ${
        isHigh
          ? "text-neon-lime animate-trend-bounce"
          : isMid
            ? "text-neon-amber"
            : "text-muted-foreground/50"
      }`}
    >
      {isHigh ? "▲" : isMid ? "→" : "▼"}
    </span>
  );
}

function MiniSparkline({ value, color }: { value: number; color: string }) {
  // Generate a simple 5-bar mini sparkline based on the value
  const bars = [0.3, 0.6, 0.4, 0.8, 1.0].map((m) =>
    Math.max(2, Math.round(m * (value / 100) * 12))
  );
  const barColor = colorMap[color]?.replace("bg-", "bg-") || "bg-neon-lime";
  return (
    <div className="flex items-end gap-px h-3 ml-1 overflow-hidden">
      {bars.map((h, i) => (
        <div
          key={i}
          className={`w-[2px] rounded-full ${barColor} opacity-60`}
          style={{ height: `${h}px` }}
        />
      ))}
    </div>
  );
}

export function IndicatorDashboard() {
  const activeCount = indicators.filter((i) => i.active).length;

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-amber animate-glow-pulse" />
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Indicators
          </span>
        </div>
        <span className="text-[10px] font-mono text-neon-lime tabular-nums">
          {activeCount}/{indicators.length} ACTIVE
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 p-3">
        {indicators.map((ind) => (
          <div
            key={ind.id}
            className={`flex items-center gap-2.5 px-2.5 py-2.5 rounded-md border transition-all duration-300 ${
              ind.active
                ? `border-border/60 bg-secondary/40 ${ind.value > 75 ? glowMap[ind.color] || "" : ""}`
                : "border-transparent bg-secondary/15 opacity-40"
            }`}
          >
            {/* Icon with active glow dot */}
            <div className="relative shrink-0">
              <span className="text-sm">{ind.icon}</span>
              {ind.active && (
                <div
                  className={`absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full ${colorMap[ind.color] || "bg-neon-lime"} ${dotGlowMap[ind.color] || ""} animate-glow-pulse`}
                />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono text-muted-foreground truncate">
                  {ind.label}
                </span>
                <div className="flex items-center">
                  <span
                    className={`text-[10px] font-mono font-bold tabular-nums ${
                      ind.active && ind.value > 75
                        ? "text-neon-lime neon-text-lime"
                        : "text-muted-foreground"
                    }`}
                  >
                    {ind.value}
                  </span>
                  <TrendArrow value={ind.value} active={ind.active} />
                  {ind.active && (
                    <MiniSparkline value={ind.value} color={ind.color} />
                  )}
                </div>
              </div>
              <div className="h-1 rounded-full bg-secondary overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    colorMap[ind.color] || "bg-neon-lime"
                  } ${ind.active && ind.value > 75 ? "animate-glow-pulse" : ""}`}
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
