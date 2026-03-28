"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function ShortsPreviewModal({
  open,
  onOpenChange,
  shortId,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  shortId: string | null;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm bg-card border-border p-0 overflow-hidden">
        <DialogHeader className="px-5 py-4 border-b border-border">
          <DialogTitle className="text-sm font-mono font-bold tracking-wider">
            <span className="text-neon-lime">GENERATE SHORTS</span>
          </DialogTitle>
        </DialogHeader>

        <div className="px-5 py-5 space-y-4">
          <p className="text-sm text-muted-foreground leading-relaxed">
            Auto-generate 3 Shorts templates from this highlight:
          </p>

          <div className="space-y-2">
            {[
              { name: "Blur Fill", desc: "Original center + blur background", rec: true },
              { name: "Letterbox", desc: "Original + black bars + caption" },
              { name: "Cam Split", desc: "Game top + cam bottom" },
            ].map((t) => (
              <div key={t.name} className="flex items-center gap-3 px-3 py-2 rounded-md bg-secondary/30 border border-border">
                <div className="w-8 h-12 rounded bg-secondary/60 border border-border shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono font-bold text-foreground">{t.name}</span>
                    {t.rec && (
                      <span className="text-[8px] font-mono font-bold px-1.5 py-0.5 rounded bg-neon-lime/15 text-neon-lime border border-neon-lime/20">
                        REC
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-muted-foreground">{t.desc}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              className="flex-1 h-9 font-mono text-xs font-bold tracking-wider bg-neon-lime text-black hover:bg-neon-lime/80"
              onClick={() => onOpenChange(false)}
            >
              GENERATE ALL
            </Button>
            <Button
              variant="outline"
              className="h-9 px-4 font-mono text-xs"
              onClick={() => onOpenChange(false)}
            >
              CANCEL
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
