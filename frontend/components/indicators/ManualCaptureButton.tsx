"use client";

import { useState, useCallback, useRef } from "react";

export function ManualCaptureButton({ onCapture }: { onCapture: (holdDurationMs: number) => void }) {
  const [isHolding, setIsHolding] = useState(false);
  const [holdSeconds, setHoldSeconds] = useState(0);
  const [justCaptured, setJustCaptured] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  const startHold = useCallback(() => {
    setIsHolding(true);
    setHoldSeconds(0);
    startTimeRef.current = Date.now();
    intervalRef.current = setInterval(() => {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      setHoldSeconds(Math.floor(elapsed));
    }, 100);
  }, []);

  const stopHold = useCallback(() => {
    const duration = Date.now() - startTimeRef.current;
    if (duration > 500) {
      // Minimum 0.5s hold to register
      onCapture(duration);
      setJustCaptured(true);
      setTimeout(() => setJustCaptured(false), 2000);
    }
    setIsHolding(false);
    setHoldSeconds(0);
    if (intervalRef.current) clearInterval(intervalRef.current);
  }, [onCapture]);

  const formatHold = (s: number) => {
    if (s < 1) return "0s";
    return `${s}s`;
  };

  return (
    <div className="px-3 py-3">
      <button
        onMouseDown={startHold}
        onMouseUp={stopHold}
        onMouseLeave={stopHold}
        className={`relative w-full h-12 rounded-lg font-mono text-xs font-bold uppercase tracking-widest transition-all overflow-hidden ${
          justCaptured
            ? "bg-neon-lime/15 border-2 border-neon-lime text-neon-lime"
            : isHolding
              ? "bg-neon-red/10 border-2 border-neon-red text-neon-red"
              : "bg-secondary/50 border-2 border-dashed border-muted-foreground/25 text-muted-foreground hover:border-neon-lime/40 hover:text-neon-lime/70"
        }`}
      >
        {isHolding && (
          <div className="absolute left-0 top-0 bottom-0 bg-neon-red/15 animate-neon-pulse" style={{ width: "100%" }} />
        )}
        <span className="relative z-10">
          {justCaptured
            ? "✓ CAPTURED — SHORTS CANDIDATE ADDED"
            : isHolding
              ? `● REC ${formatHold(holdSeconds)} — RELEASE TO CREATE SHORT`
              : "HOLD TO CAPTURE"}
        </span>
      </button>
      <p className="text-[9px] font-mono text-muted-foreground/40 text-center mt-1.5 tracking-wider">
        HOLD TO MARK HIGHLIGHT — RELEASE TO CREATE SHORTS CANDIDATE
      </p>
    </div>
  );
}
