"use client";

import { useState, type KeyboardEvent } from "react";

export function LandingScreen({
  onConnect,
}: {
  onConnect: (url: string) => void;
}) {
  const [url, setUrl] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && url.trim()) {
      onConnect(url.trim());
    }
  };

  return (
    <div className="h-screen bg-background flex flex-col items-center justify-center relative overflow-hidden">
      {/* Background grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `
            linear-gradient(oklch(0.795 0.184 128.25) 1px, transparent 1px),
            linear-gradient(90deg, oklch(0.795 0.184 128.25) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Glow orb */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-neon-lime/[0.02] blur-[150px]" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-8 w-full max-w-xl px-6">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-xl bg-neon-lime flex items-center justify-center">
            <svg width="28" height="28" viewBox="0 0 16 16" fill="none">
              <path d="M4 3L12 8L4 13V3Z" fill="black" />
            </svg>
          </div>
          <div>
            <h1 className="font-mono text-2xl font-bold tracking-wider text-foreground">
              LIVE<span className="text-neon-lime">O</span>
            </h1>
            <p className="text-[10px] font-mono uppercase tracking-[0.3em] text-muted-foreground">
              Live Stream → Shorts Generator
            </p>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-muted-foreground text-center leading-relaxed max-w-md">
          Analyze game live streams in real-time,
          <br />
          <span className="text-foreground font-medium">
            auto-detect highlight moments
          </span>
          {" "}and generate Shorts.
        </p>

        {/* URL Input */}
        <div className="w-full">
          <div
            className={`relative w-full rounded-xl border-2 transition-all duration-300 ${
              isFocused
                ? "border-neon-lime/60"
                : "border-border hover:border-muted-foreground/30"
            }`}
          >
            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714Z" />
              </svg>
            </div>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onKeyDown={handleKeyDown}
              placeholder="Paste a Twitch channel URL..."
              className="w-full h-14 bg-transparent pl-12 pr-24 text-sm font-mono text-foreground placeholder:text-muted-foreground/40 focus:outline-none"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded border border-border bg-secondary/60 text-[10px] font-mono text-muted-foreground">
                ENTER ↵
              </kbd>
            </div>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground/50 text-center mt-3 tracking-wider">
            e.g. https://www.twitch.tv/valorant
          </p>
        </div>

        {/* Indicators preview */}
        <div className="flex flex-wrap justify-center gap-2 mt-4">
          {[
            { icon: "💬", label: "Chat Velocity" },
            { icon: "🔊", label: "Audio Spike" },
            { icon: "💰", label: "Super Chat" },
            { icon: "😂", label: "Emote Flood" },
            { icon: "🔥", label: "Sentiment" },
            { icon: "🎯", label: "Kill Event" },
            { icon: "🔑", label: "Keyword" },
            { icon: "👁", label: "Viewer Spike" },
          ].map((ind) => (
            <div
              key={ind.label}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-border bg-secondary/30 text-[10px] font-mono text-muted-foreground"
            >
              <span className="text-xs">{ind.icon}</span>
              {ind.label}
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="absolute bottom-6 text-[10px] font-mono text-muted-foreground/30 tracking-wider">
        LIVEO — HACKATHON 2026
      </div>
    </div>
  );
}
