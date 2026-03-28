"use client";

import { useDeferredValue, useState } from "react";
import type { DebugLogEntry, StreamStatus } from "@/lib/types";

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDetails(details?: Record<string, unknown>) {
  if (!details || Object.keys(details).length === 0) {
    return "";
  }

  const raw = JSON.stringify(details);
  return raw.length > 240 ? `${raw.slice(0, 240)}...` : raw;
}

function levelClass(level: DebugLogEntry["level"]) {
  switch (level) {
    case "error":
      return "border-neon-red/40 text-neon-red";
    case "warning":
      return "border-neon-amber/40 text-neon-amber";
    case "debug":
      return "border-neon-cyan/40 text-neon-cyan";
    default:
      return "border-neon-lime/30 text-neon-lime";
  }
}

export function DebugConsole({
  logs,
  wsConnected,
  streamStatus,
  streamUrl,
  candidateCount,
  generatedCount,
}: {
  logs: DebugLogEntry[];
  wsConnected: boolean;
  streamStatus: StreamStatus;
  streamUrl?: string | null;
  candidateCount: number;
  generatedCount: number;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const deferredLogs = useDeferredValue(logs);
  const recentLogs = deferredLogs.slice(-60).reverse();
  const backendLogCount = deferredLogs.filter((entry) => entry.origin === "backend").length;
  const frontendLogCount = deferredLogs.length - backendLogCount;

  return (
    <div className="fixed right-4 bottom-4 z-50 w-[min(460px,calc(100vw-2rem))]">
      <div className="overflow-hidden rounded-2xl border border-border bg-card/95 shadow-[0_20px_80px_oklch(0.06_0.02_285/0.85)] backdrop-blur-xl">
        <div className="flex items-center justify-between gap-3 border-b border-border bg-secondary/30 px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-neon-cyan animate-neon-pulse" />
              <span className="text-[10px] font-mono uppercase tracking-[0.28em] text-muted-foreground">
                Debug Console
              </span>
            </div>
            <p className="mt-1 truncate text-[11px] font-mono text-muted-foreground/70">
              {streamUrl ?? "No stream URL"}
            </p>
          </div>

          <button
            type="button"
            onClick={() => setCollapsed((current) => !current)}
            className="rounded-md border border-border px-2 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:text-foreground"
          >
            {collapsed ? "Open" : "Hide"}
          </button>
        </div>

        {!collapsed && (
          <>
            <div className="grid grid-cols-2 gap-2 border-b border-border bg-background/60 px-4 py-3">
              <div className="rounded-xl border border-border bg-secondary/20 px-3 py-2">
                <div className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground/80">
                  Backend
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${streamStatus.isLive ? "bg-neon-lime" : "bg-neon-red"}`} />
                  <span className="text-xs font-mono text-foreground">
                    {streamStatus.isLive ? "Live" : "Idle"}
                  </span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-muted-foreground/70">
                  {streamStatus.captureMethod || "capture: n/a"} · {streamStatus.segmentCount} seg
                </div>
              </div>

              <div className="rounded-xl border border-border bg-secondary/20 px-3 py-2">
                <div className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground/80">
                  Frontend
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${wsConnected ? "bg-neon-cyan" : "bg-neon-red"}`} />
                  <span className="text-xs font-mono text-foreground">
                    {wsConnected ? "WS Connected" : "WS Reconnecting"}
                  </span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-muted-foreground/70">
                  {candidateCount} candidates · {generatedCount} shorts
                </div>
              </div>
            </div>

            {streamStatus.error && (
              <div className="border-b border-neon-red/20 bg-neon-red/8 px-4 py-2 text-[11px] font-mono text-neon-red">
                Backend error: {streamStatus.error}
              </div>
            )}

            <div className="flex items-center justify-between border-b border-border px-4 py-2">
              <span className="text-[10px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
                Recent Logs
              </span>
              <span className="text-[10px] font-mono text-muted-foreground/70">
                {backendLogCount} backend / {frontendLogCount} frontend
              </span>
            </div>

            <div className="max-h-[360px] overflow-y-auto bg-[linear-gradient(180deg,oklch(0.11_0.01_285)_0%,oklch(0.09_0.008_285)_100%)] px-4 py-3">
              {recentLogs.length === 0 && (
                <div className="rounded-xl border border-dashed border-border px-3 py-5 text-center text-[11px] font-mono text-muted-foreground/60">
                  Waiting for frontend or backend events...
                </div>
              )}

              <div className="space-y-2">
                {recentLogs.map((entry) => {
                  const details = formatDetails(entry.details);
                  return (
                    <div
                      key={entry.id}
                      className="rounded-xl border border-border/70 bg-background/60 px-3 py-2.5"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-muted-foreground/60">
                          {formatTimestamp(entry.timestamp)}
                        </span>
                        <span className={`rounded-full border px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-[0.14em] ${levelClass(entry.level)}`}>
                          {entry.level}
                        </span>
                        <span className="rounded-full border border-border px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-[0.14em] text-muted-foreground/80">
                          {entry.origin === "backend" ? "BE" : "UI"}
                        </span>
                        <span className="truncate text-[10px] font-mono text-muted-foreground/60">
                          {entry.source}
                        </span>
                      </div>
                      <div className="mt-2 text-[12px] text-foreground">
                        {entry.message}
                      </div>
                      <div className="mt-1 text-[10px] font-mono uppercase tracking-[0.14em] text-muted-foreground/55">
                        {entry.event}
                      </div>
                      {details && (
                        <pre className="mt-2 overflow-x-auto rounded-lg border border-border/70 bg-black/20 px-2 py-1.5 text-[10px] font-mono text-muted-foreground/75 whitespace-pre-wrap break-all">
                          {details}
                        </pre>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
