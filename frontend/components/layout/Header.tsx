"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";

export function Header({ onSettingsOpen }: { onSettingsOpen: () => void }) {
  const [elapsed, setElapsed] = useState(0);
  const [connected, setConnected] = useState(true);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-5 gap-4 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-md bg-neon-lime flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 3L12 8L4 13V3Z" fill="black" />
          </svg>
        </div>
        <span className="font-mono text-sm font-bold tracking-wider text-foreground">
          SHORTS<span className="text-neon-lime">FACTORY</span>
        </span>
      </div>

      <div className="w-px h-6 bg-border" />

      {/* Stream URL */}
      <div className="flex items-center gap-2 flex-1 max-w-md">
        <div className="flex-1 h-8 rounded-md bg-secondary/60 border border-border px-3 flex items-center">
          <span className="text-xs font-mono text-muted-foreground truncate">
            youtube.com/watch?v=RQFpfJBItUY
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${
              connected
                ? "bg-neon-lime neon-glow-lime animate-neon-pulse"
                : "bg-destructive"
            }`}
          />
          <span className="text-xs font-mono text-muted-foreground">
            {connected ? "LIVE" : "OFFLINE"}
          </span>
        </div>
      </div>

      <div className="flex-1" />

      {/* Stats */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
            REC
          </span>
          <div className="w-2 h-2 rounded-full bg-neon-red animate-neon-pulse" />
          <span className="font-mono text-sm text-foreground tabular-nums">
            {formatTime(elapsed)}
          </span>
        </div>

        <div className="w-px h-6 bg-border" />

        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
            SHORTS
          </span>
          <span className="font-mono text-sm text-neon-cyan neon-text-cyan">
            3
          </span>
        </div>

        <div className="w-px h-6 bg-border" />

        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
            QUEUE
          </span>
          <span className="font-mono text-sm text-neon-amber">2</span>
        </div>
      </div>

      <div className="w-px h-6 bg-border" />

      <Button
        variant="ghost"
        size="sm"
        onClick={onSettingsOpen}
        className="h-8 px-2.5 text-muted-foreground hover:text-foreground"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </Button>
    </header>
  );
}
