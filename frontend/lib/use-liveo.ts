"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api, connectWebSocket } from "./api";
import type { ShortsCandidate, GeneratedShort } from "./types";

export function useLiveO() {
  const [isLive, setIsLive] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [candidates, setCandidates] = useState<ShortsCandidate[]>([]);
  const [generatedShorts, setGeneratedShorts] = useState<GeneratedShort[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const elapsedRef = useRef(0);

  useEffect(() => {
    if (!isLive) return;
    const timer = setInterval(() => {
      elapsedRef.current += 1;
      setElapsed(elapsedRef.current);
    }, 1000);
    return () => clearInterval(timer);
  }, [isLive]);

  const handleWSMessage = useCallback((msg: { type: string; data: Record<string, unknown> }) => {
    switch (msg.type) {
      case "stream_status": {
        const d = msg.data as { isLive: boolean; elapsed: number };
        setIsLive(d.isLive);
        if (!d.isLive) {
          elapsedRef.current = 0;
          setElapsed(0);
        }
        break;
      }
      case "candidate_created":
        setCandidates((prev) => [msg.data as unknown as ShortsCandidate, ...prev]);
        break;
      case "candidate_updated":
        setCandidates((prev) =>
          prev.map((c) =>
            c.id === (msg.data as { id: string }).id
              ? { ...c, ...(msg.data as Partial<ShortsCandidate>) }
              : c,
          ),
        );
        break;
      case "candidate_deleted":
        setCandidates((prev) =>
          prev.filter((c) => c.id !== (msg.data as { id: string }).id),
        );
        break;
      case "generate_progress":
        setCandidates((prev) =>
          prev.map((c) =>
            c.id === (msg.data as { candidateId: string }).candidateId
              ? { ...c, progress: (msg.data as { percent: number }).percent }
              : c,
          ),
        );
        break;
      case "generate_complete": {
        const gs = (msg.data as { generatedShort: GeneratedShort }).generatedShort;
        if (gs) setGeneratedShorts((prev) => [gs, ...prev]);
        break;
      }
    }
  }, []);

  const connectWS = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return;
    const ws = connectWebSocket(handleWSMessage);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connectWS, 3000);
    };
    wsRef.current = ws;
  }, [handleWSMessage]);

  useEffect(() => {
    connectWS();
    return () => {
      wsRef.current?.close();
    };
  }, [connectWS]);

  const startStream = useCallback(async (source: string, url?: string) => {
    await api.stream.start(source, url);
    setIsLive(true);
    elapsedRef.current = 0;
    setElapsed(0);
  }, []);

  const stopStream = useCallback(async () => {
    await api.stream.stop();
    setIsLive(false);
  }, []);

  const createCandidate = useCallback(async (data: Record<string, unknown>) => {
    const c = await api.candidates.create(data);
    return c;
  }, []);

  const updateCandidate = useCallback(async (id: string, data: Record<string, unknown>) => {
    await api.candidates.update(id, data);
  }, []);

  const deleteCandidate = useCallback(async (id: string) => {
    await api.candidates.delete(id);
    setCandidates((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const generateShort = useCallback(async (data: Record<string, unknown>) => {
    return api.shorts.generate(data);
  }, []);

  return {
    isLive,
    elapsed,
    connected,
    candidates,
    generatedShorts,
    startStream,
    stopStream,
    createCandidate,
    updateCandidate,
    deleteCandidate,
    generateShort,
    setCandidates,
  };
}
