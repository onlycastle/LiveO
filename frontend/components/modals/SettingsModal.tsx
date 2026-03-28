"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Slider } from "@/components/ui/slider";
import { indicators } from "@/lib/mock-data";

/* ── Section header ── */
function SectionHeader({
  label,
  color = "text-neon-lime",
}: {
  label: string;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-2 pt-1">
      <span
        className={`text-[9px] font-mono font-bold uppercase tracking-[0.15em] ${color}`}
      >
        {label}
      </span>
      <div className="flex-1 h-px bg-border/50" />
    </div>
  );
}

export function SettingsModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [selectedDuration, setSelectedDuration] = useState("30s");
  const [autoConfirmThreshold, setAutoConfirmThreshold] = useState(85);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-card border-border p-0 overflow-hidden">
        <DialogHeader className="px-5 pt-5 pb-0">
          <DialogTitle className="text-sm font-mono font-bold tracking-wider">
            <span className="text-neon-lime">SETTINGS</span>
          </DialogTitle>
        </DialogHeader>

        {/* Scrollable body */}
        <div className="max-h-[70vh] overflow-y-auto px-5 pb-5 space-y-5">
          {/* ═══ CONNECTION ═══ */}
          <SectionHeader label="Connection" color="text-neon-cyan" />

          <div>
            <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2 block">
              Twitch Client ID
            </label>
            <input
              type="password"
              placeholder="AIza..."
              className="w-full h-8 rounded-md bg-secondary/60 border border-border px-3 text-xs font-mono text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-neon-cyan/50 transition-shadow"
            />
          </div>

          {/* ═══ DETECTION ═══ */}
          <SectionHeader label="Detection" color="text-neon-violet" />

          <div>
            <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-3 block">
              Indicator Sensitivity
            </label>
            <div className="space-y-3">
              {indicators.map((ind) => (
                <div key={ind.id} className="flex items-center gap-3">
                  <span className="text-sm w-5">{ind.icon}</span>
                  <span className="text-[10px] font-mono text-muted-foreground w-20 truncate">
                    {ind.label}
                  </span>
                  <Slider
                    defaultValue={[ind.value]}
                    min={0}
                    max={100}
                    step={5}
                    className="flex-1"
                  />
                  <span className="text-[10px] font-mono text-foreground tabular-nums w-6 text-right">
                    {ind.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2 block">
              Auto-confirm threshold
            </label>
            <div className="flex items-center gap-3">
              <Slider
                value={[autoConfirmThreshold]}
                onValueChange={(v) => setAutoConfirmThreshold(Array.isArray(v) ? v[0] : v)}
                min={50}
                max={100}
                step={5}
                className="flex-1"
              />
              <span className="text-[10px] font-mono text-neon-lime tabular-nums w-8 text-right">
                {autoConfirmThreshold}%
              </span>
            </div>
            <p className="text-[9px] font-mono text-muted-foreground/60 mt-1">
              Candidates above this confidence will auto-confirm
            </p>
          </div>

          {/* ═══ OUTPUT ═══ */}
          <SectionHeader label="Output" color="text-neon-amber" />

          <div>
            <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-2 block">
              Shorts Duration
            </label>
            <div className="flex gap-2">
              {["15s", "30s", "45s", "60s"].map((d) => (
                <button
                  key={d}
                  onClick={() => setSelectedDuration(d)}
                  className={`flex-1 h-7 rounded text-[10px] font-mono font-bold transition-all ${
                    d === selectedDuration
                      ? "border-2 border-neon-lime text-neon-lime bg-neon-lime/10"
                      : "border border-border text-muted-foreground hover:border-muted-foreground/50 hover:text-foreground/70"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
