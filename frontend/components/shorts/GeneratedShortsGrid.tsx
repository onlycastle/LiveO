"use client";

import { generatedShorts } from "@/lib/mock-data";

export function GeneratedShortsGrid() {
  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-lime" />
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Generated Shorts
          </span>
        </div>
        <span className="text-[10px] font-mono text-neon-lime tabular-nums">
          {generatedShorts.length} READY
        </span>
      </div>
      <div className="flex gap-3 p-3 overflow-x-auto scrollbar-none">
        {generatedShorts.map((short) => (
          <div
            key={short.id}
            className="group relative shrink-0 w-28 rounded-lg border border-border bg-secondary/30 overflow-hidden hover:border-neon-lime/40 transition-all cursor-pointer"
          >
            <div className="aspect-[9/14] bg-gradient-to-b from-secondary to-background relative">
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5">
                <div className="w-8 h-8 rounded-full bg-neon-lime/10 border border-neon-lime/30 flex items-center justify-center group-hover:bg-neon-lime/20 transition-colors">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" className="text-neon-lime ml-0.5">
                    <path d="M4 3L12 8L4 13V3Z" />
                  </svg>
                </div>
                <span className="text-[8px] font-mono text-muted-foreground tabular-nums">
                  {short.duration}
                </span>
              </div>
              <div className="absolute bottom-0 inset-x-0 h-12 bg-gradient-to-t from-black/80 to-transparent" />
              <div className="absolute bottom-0 inset-x-0 p-1.5">
                <p className="text-[9px] font-medium text-white leading-tight line-clamp-2 break-words">
                  {short.title}
                </p>
              </div>
            </div>
            <div className="px-1.5 py-1 flex items-center justify-between min-w-0">
              <span className="text-[8px] font-mono text-muted-foreground truncate">
                {short.createdAt}
              </span>
              <button className="text-[8px] font-mono text-neon-cyan hover:text-neon-cyan/80 transition-colors shrink-0 ml-1">
                DL
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
