"use client";

import { useState, useCallback, useRef } from "react";

export function ManualCaptureButton({ onCapture }: { onCapture: (holdDurationMs: number) => void }) {
  const [isHolding, setIsHolding] = useState(false);
  const [holdSeconds, setHoldSeconds] = useState(0);
  const [justCaptured, setJustCaptured] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const isHoldingRef = useRef(false);

  const clearHoldInterval = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startHold = useCallback(() => {
    setIsHolding(true);
    isHoldingRef.current = true;
    setHoldSeconds(0);
    startTimeRef.current = Date.now();
    clearHoldInterval();
    intervalRef.current = setInterval(() => {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      setHoldSeconds(Math.floor(elapsed));
    }, 200);
  }, [clearHoldInterval]);

  const stopHold = useCallback(() => {
    if (!isHoldingRef.current) return;
    isHoldingRef.current = false;
    const duration = Date.now() - startTimeRef.current;
    clearHoldInterval();
    setIsHolding(false);
    setHoldSeconds(0);

    // Minimum 1 second hold to register a capture
    if (duration >= 1000) {
      onCapture(duration);
      setJustCaptured(true);
      setTimeout(() => setJustCaptured(false), 2000);
    }
  }, [onCapture, clearHoldInterval]);

  const cancelHold = useCallback(() => {
    // Mouse leave just cancels without capturing
    if (!isHoldingRef.current) return;
    isHoldingRef.current = false;
    clearHoldInterval();
    setIsHolding(false);
    setHoldSeconds(0);
  }, [clearHoldInterval]);

  const formatHold = (s: number) => (s < 1 ? "0s" : `${s}s`);

  return (
    <div className="px-3 py-3">
      <button
        onMouseDown={startHold}
        onMouseUp={stopHold}
        onMouseLeave={cancelHold}
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
            ? "✓ CAPTURED"
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
