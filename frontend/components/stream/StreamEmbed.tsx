"use client";

export function StreamEmbed() {
  return (
    <div className="relative w-full aspect-video rounded-lg overflow-hidden border border-border bg-black">
      <iframe
        src="https://player.twitch.tv/?channel=valorant&parent=localhost"
        className="absolute inset-0 w-full h-full"
        allowFullScreen
        title="Live Stream"
      />
      {/* HUD overlay */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Scan-line at top */}
        <div className="absolute top-0 left-0 right-0 h-16 overflow-hidden">
          <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-neon-cyan/40 to-transparent animate-scan-line" />
        </div>

        {/* HUD corners — thinner, longer brackets with glow */}
        {/* Top-left */}
        <div className="absolute top-0 left-0">
          <div className="absolute top-0 left-0 w-8 h-px bg-gradient-to-r from-neon-lime/40 to-transparent" />
          <div className="absolute top-0 left-0 h-8 w-px bg-gradient-to-b from-neon-lime/40 to-transparent" />
        </div>
        {/* Top-right */}
        <div className="absolute top-0 right-0">
          <div className="absolute top-0 right-0 w-8 h-px bg-gradient-to-l from-neon-lime/40 to-transparent" />
          <div className="absolute top-0 right-0 h-8 w-px bg-gradient-to-b from-neon-lime/40 to-transparent" />
        </div>
        {/* Bottom-left */}
        <div className="absolute bottom-0 left-0">
          <div className="absolute bottom-0 left-0 w-8 h-px bg-gradient-to-r from-neon-lime/40 to-transparent" />
          <div className="absolute bottom-0 left-0 h-8 w-px bg-gradient-to-t from-neon-lime/40 to-transparent" />
        </div>
        {/* Bottom-right */}
        <div className="absolute bottom-0 right-0">
          <div className="absolute bottom-0 right-0 w-8 h-px bg-gradient-to-l from-neon-lime/40 to-transparent" />
          <div className="absolute bottom-0 right-0 h-8 w-px bg-gradient-to-t from-neon-lime/40 to-transparent" />
        </div>

        {/* LIVE badge — refined pill with recording dot */}
        <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5 bg-neon-red/90 backdrop-blur-sm px-2.5 py-1 rounded-full shadow-[0_0_12px_oklch(0.637_0.237_15.163/0.5)]">
          <div className="relative w-1.5 h-1.5">
            <div className="absolute inset-0 rounded-full bg-white animate-neon-pulse" />
            <div className="absolute -inset-0.5 rounded-full bg-white/30 animate-neon-pulse" />
          </div>
          <span className="text-[9px] font-mono font-bold text-white tracking-[0.15em]">
            LIVE
          </span>
        </div>

        {/* Timestamp overlay bottom-left */}
        <div className="absolute bottom-2.5 left-2.5 flex items-center gap-1.5">
          <div className="w-1 h-1 rounded-full bg-neon-cyan/60 animate-neon-pulse" />
          <span className="text-[9px] font-mono text-white/50 tracking-wider">
            REC 01:24:18
          </span>
        </div>
      </div>
    </div>
  );
}
