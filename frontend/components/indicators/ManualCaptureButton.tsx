"use client";

import { useState, useCallback, useRef } from "react";

export function ManualCaptureButton({ onCapture }: { onCapture: () => void }) {
  const [isHolding, setIsHolding] = useState(false);
  const [holdProgress, setHoldProgress] = useState(0);
  const [justCaptured, setJustCaptured] = useState(false);
  const [showBurst, setShowBurst] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const capturedRef = useRef(false);

  const startHold = useCallback(() => {
    setIsHolding(true);
    setHoldProgress(0);
    capturedRef.current = false;
    intervalRef.current = setInterval(() => {
      setHoldProgress((p) => {
        if (p >= 100) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          if (!capturedRef.current) {
            capturedRef.current = true;
            queueMicrotask(() => onCapture());
          }
          return 100;
        }
        return p + 2;
      });
    }, 30);
  }, [onCapture]);

  const stopHold = useCallback(() => {
    if (holdProgress >= 100) {
      setJustCaptured(true);
      setShowBurst(true);
      setTimeout(() => setShowBurst(false), 800);
      setTimeout(() => setJustCaptured(false), 2500);
    }
    setIsHolding(false);
    setHoldProgress(0);
    if (intervalRef.current) clearInterval(intervalRef.current);
  }, [holdProgress]);

  return (
    <div className="px-3 py-3">
      <div className="relative">
        {/* Pulsing ring during hold */}
        {isHolding && (
          <div className="absolute -inset-1 rounded-xl border-2 border-neon-red/60 animate-capture-ring" />
        )}
        {isHolding && holdProgress > 50 && (
          <div className="absolute -inset-2 rounded-xl border border-neon-red/30 animate-capture-ring" style={{ animationDelay: "0.3s" }} />
        )}

        {/* Success burst particles */}
        {showBurst && (
          <>
            <div className="absolute inset-0 rounded-lg bg-neon-lime/20 animate-particle-burst" />
            <div className="absolute -inset-3 rounded-xl border border-neon-lime/40 animate-particle-burst" style={{ animationDelay: "0.1s" }} />
            <div className="absolute -inset-6 rounded-2xl border border-neon-lime/20 animate-particle-burst" style={{ animationDelay: "0.2s" }} />
          </>
        )}

        {/* Success glow behind button */}
        {justCaptured && (
          <div className="absolute -inset-1 rounded-xl bg-neon-lime/10 blur-md" />
        )}

        <button
          onMouseDown={startHold}
          onMouseUp={stopHold}
          onMouseLeave={stopHold}
          className={`relative w-full h-12 rounded-lg font-mono text-xs font-bold uppercase tracking-widest transition-all duration-200 overflow-hidden ${
            justCaptured
              ? "bg-neon-lime/15 border-2 border-neon-lime text-neon-lime neon-glow-lime"
              : isHolding
                ? "bg-neon-red/10 border-2 border-neon-red text-neon-red"
                : "bg-secondary/60 border-2 border-dashed border-muted-foreground/30 text-muted-foreground hover:border-neon-red/50 hover:text-neon-red/80 hover:bg-secondary/80"
          }`}
        >
          {/* Progress fill with gradient */}
          {isHolding && (
            <div
              className="absolute inset-0 bg-gradient-to-r from-neon-red/10 via-neon-red/25 to-neon-red/10 transition-all duration-75"
              style={{ width: `${holdProgress}%` }}
            />
          )}

          {/* Threshold marker at center */}
          {isHolding && holdProgress < 100 && (
            <div className="absolute top-0 bottom-0 left-1/2 w-px bg-neon-red/20" />
          )}

          <span className="relative z-10 flex items-center justify-center gap-2">
            {justCaptured ? (
              <>
                <span className="inline-block animate-neon-pulse">✓</span>
                CAPTURED — SHORTS CANDIDATE ADDED
              </>
            ) : isHolding ? (
              holdProgress >= 100 ? (
                "CAPTURED!"
              ) : (
                <>
                  <span className="inline-block w-3 h-3 rounded-full border-2 border-neon-red/60" style={{
                    background: `conic-gradient(oklch(0.637 0.237 15.163 / 0.6) ${holdProgress * 3.6}deg, transparent ${holdProgress * 3.6}deg)`
                  }} />
                  {`CAPTURING... ${holdProgress}%`}
                </>
              )
            ) : (
              "HOLD TO CAPTURE"
            )}
          </span>
        </button>
      </div>
      <p className="text-[9px] font-mono text-muted-foreground/50 text-center mt-2 tracking-wider">
        HOLD 1.5s TO MARK HIGHLIGHT — CREATES SHORTS FROM TRANSCRIPT CONTEXT
      </p>
    </div>
  );
}
