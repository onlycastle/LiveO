"use client";

import { startTransition, useCallback, useEffect, useRef, useState } from "react";
import type {
  DebugLogEntry,
  DebugLogLevel,
  GeneratedShort,
  Indicator,
  ShortsCandidate,
  StreamStatus,
  TranscriptLine,
} from "./types";

function resolveApiUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return configured;
  }

  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000";
  }

  const isSecure = window.location.protocol === "https:";
  const protocol = isSecure ? "https:" : "http:";
  return `${protocol}//${window.location.hostname}:8000`;
}

function resolveWsUrl(): string {
  const configured = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (configured) {
    return configured;
  }

  if (typeof window === "undefined") {
    return "ws://localhost:8000/ws/events";
  }

  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.hostname}:8000/ws/events`;
}

const API = resolveApiUrl();
const WS_URL = resolveWsUrl();
const MAX_DEBUG_LOGS = 180;
const MAX_TRANSCRIPT_LINES = 250;

type JsonRecord = Record<string, unknown>;
type CandidateCreateInput = Omit<ShortsCandidate, "id" | "progress"> & {
  status?: ShortsCandidate["status"];
};

const DEFAULT_STREAM_STATUS: StreamStatus = {
  isLive: false,
  elapsed: 0,
  captureMethod: "",
  error: null,
  segmentCount: 0,
  sttAvailable: true,
};

const DEFAULT_INDICATORS: Indicator[] = [
  { id: "1", type: "chat_velocity", label: "Chat Velocity", icon: "\u{1F4AC}", value: 0, color: "neon-lime", active: false },
  { id: "2", type: "audio_spike", label: "Audio Spike", icon: "\u{1F50A}", value: 0, color: "neon-red", active: false },
  { id: "3", type: "superchat", label: "Super Chat", icon: "\u{1F4B0}", value: 0, color: "neon-amber", active: false },
  { id: "4", type: "emote_flood", label: "Emote Flood", icon: "\u{1F602}", value: 0, color: "neon-cyan", active: false },
  { id: "5", type: "sentiment_shift", label: "Sentiment", icon: "\u{1F525}", value: 0, color: "neon-violet", active: false },
  { id: "6", type: "viewer_spike", label: "Viewer Spike", icon: "\u{1F441}", value: 0, color: "neon-cyan", active: false },
  { id: "7", type: "kill_event", label: "Kill Event", icon: "\u{1F3AF}", value: 0, color: "neon-red", active: false },
  { id: "8", type: "keyword", label: "Keyword Hit", icon: "\u{1F511}", value: 0, color: "neon-lime", active: false },
];

function limitItems<T>(items: T[], maxItems: number) {
  return items.length > maxItems ? items.slice(items.length - maxItems) : items;
}

function normalizeLogLevel(level: unknown): DebugLogLevel {
  if (level === "debug" || level === "warning" || level === "error") {
    return level;
  }
  return "info";
}

function parseJsonMaybe(text: string): unknown {
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function isShortsCandidate(value: unknown): value is ShortsCandidate {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.id === "string" && typeof record.status === "string";
}

function normalizeDetails(details: unknown): Record<string, unknown> | undefined {
  if (details && typeof details === "object" && !Array.isArray(details)) {
    return details as Record<string, unknown>;
  }
  return undefined;
}

function normalizeDebugLog(input: unknown): DebugLogEntry | null {
  if (!input || typeof input !== "object") {
    return null;
  }

  const record = input as Record<string, unknown>;
  if (typeof record.id !== "string" || typeof record.message !== "string") {
    return null;
  }

  return {
    id: record.id,
    timestamp: typeof record.timestamp === "string" ? record.timestamp : new Date().toISOString(),
    origin: record.origin === "frontend" ? "frontend" : "backend",
    source: typeof record.source === "string" ? record.source : "backend.server",
    event: typeof record.event === "string" ? record.event : "unknown",
    level: normalizeLogLevel(record.level),
    message: record.message,
    details: normalizeDetails(record.details),
  };
}

function mergeDebugLogs(current: DebugLogEntry[], incoming: DebugLogEntry[]) {
  if (incoming.length === 0) {
    return current;
  }

  const merged = [...current];
  const seen = new Set(current.map((entry) => entry.id));

  for (const entry of incoming) {
    if (!seen.has(entry.id)) {
      merged.push(entry);
      seen.add(entry.id);
    }
  }

  return limitItems(merged, MAX_DEBUG_LOGS);
}

function normalizeStreamStatus(input: unknown): StreamStatus {
  if (!input || typeof input !== "object") {
    return DEFAULT_STREAM_STATUS;
  }

  const record = input as Record<string, unknown>;
  return {
    isLive: Boolean(record.isLive),
    elapsed: typeof record.elapsed === "number" ? record.elapsed : 0,
    captureMethod: typeof record.captureMethod === "string" ? record.captureMethod : "",
    error: typeof record.error === "string" ? record.error : null,
    segmentCount: typeof record.segmentCount === "number" ? record.segmentCount : 0,
    sttAvailable: typeof record.sttAvailable === "boolean" ? record.sttAvailable : true,
  };
}

function normalizeIndicator(input: unknown): Indicator | null {
  if (!input || typeof input !== "object") {
    return null;
  }

  const record = input as Record<string, unknown>;
  if (
    typeof record.id !== "string" ||
    typeof record.type !== "string" ||
    typeof record.label !== "string" ||
    typeof record.icon !== "string" ||
    typeof record.color !== "string" ||
    typeof record.value !== "number"
  ) {
    return null;
  }

  return {
    id: record.id,
    type: record.type as Indicator["type"],
    label: record.label,
    icon: record.icon,
    value: Math.max(0, Math.min(100, Math.round(record.value))),
    color: record.color,
    active: Boolean(record.active),
  };
}

function normalizeIndicators(input: unknown): Indicator[] {
  if (!Array.isArray(input)) {
    return DEFAULT_INDICATORS;
  }

  const normalized = input
    .map(normalizeIndicator)
    .filter((indicator): indicator is Indicator => indicator !== null);

  return normalized.length > 0 ? normalized : DEFAULT_INDICATORS;
}

function getErrorMessage(error: unknown) {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function normalizeError(error: unknown): Record<string, unknown> {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack,
      cause: (error as Error & { cause?: unknown }).cause,
    };
  }

  if (error && typeof error === "object") {
    const normalized: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(error)) {
      normalized[key] = value;
    }
    if (Object.keys(normalized).length === 0) {
      return { value: String(error) };
    }
    return normalized;
  }

  return { value: String(error) };
}

function getResponseErrorMessage(response: Response, payload: unknown) {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    if (typeof record.detail === "string") {
      return record.detail;
    }
    if (typeof record.message === "string") {
      return record.message;
    }
  }
  return `Request failed (${response.status})`;
}

function summarizePayload(data: JsonRecord) {
  const summary: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(data).slice(0, 8)) {
    if (typeof value === "string") {
      summary[key] = value.length > 120 ? `${value.slice(0, 120)}...` : value;
      continue;
    }
    if (Array.isArray(value)) {
      summary[key] = `[${value.length} items]`;
      continue;
    }
    if (value && typeof value === "object") {
      summary[key] = "[object]";
      continue;
    }
    summary[key] = value;
  }
  return summary;
}

export function useLiveO() {
  const [candidates, setCandidates] = useState<ShortsCandidate[]>([]);
  const [generatedShorts, setGeneratedShorts] = useState<GeneratedShort[]>([]);
  const [transcriptLines, setTranscriptLines] = useState<TranscriptLine[]>([]);
  const [indicators, setIndicators] = useState<Indicator[]>(DEFAULT_INDICATORS);
  const [streamStatus, setStreamStatus] = useState<StreamStatus>(DEFAULT_STREAM_STATUS);
  const [wsConnected, setWsConnected] = useState(false);
  const [debugLogs, setDebugLogs] = useState<DebugLogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef(0);
  const logCounterRef = useRef(0);

  const pushDebugLogs = useCallback((entries: DebugLogEntry[]) => {
    startTransition(() => {
      setDebugLogs((current) => mergeDebugLogs(current, entries));
    });
  }, []);

  const appendFrontendLog = useCallback((
    level: DebugLogLevel,
    event: string,
    message: string,
    details?: Record<string, unknown>,
    source = "frontend.use-liveo",
  ) => {
    const nextId = ++logCounterRef.current;
    const entry: DebugLogEntry = {
      id: `ui-${Date.now()}-${nextId}`,
      timestamp: new Date().toISOString(),
      origin: "frontend",
      source,
      event,
      level,
      message,
      details,
    };

    const consoleFn =
      level === "error"
        ? console.error
        : level === "warning"
          ? console.warn
          : level === "debug"
            ? console.debug
            : console.info;
    consoleFn(`[${entry.source}] ${entry.event}: ${entry.message}`, details ?? {});
    pushDebugLogs([entry]);
    return entry;
  }, [pushDebugLogs]);

  const syncStreamStatus = useCallback((partial: Partial<StreamStatus>) => {
    setStreamStatus((current) => ({
      ...current,
      ...partial,
      error: partial.error === undefined ? current.error : partial.error,
    }));
  }, []);

  const requestJson = useCallback(async <T,>(
    path: string,
    init: RequestInit | undefined,
    options: {
      event: string;
      successMessage: string;
      failureMessage: string;
    },
  ): Promise<T> => {
    const method = init?.method ?? "GET";
    appendFrontendLog("debug", `${options.event}_request`, `HTTP ${method} ${path}`, { method, path });

    try {
      const response = await fetch(`${API}${path}`, init);
      const text = await response.text();
      const payload = parseJsonMaybe(text);

      if (!response.ok) {
        appendFrontendLog("error", `${options.event}_failed`, options.failureMessage, {
          method,
          path,
          status: response.status,
          statusText: response.statusText,
          response: payload,
          responseText: text || "<empty>",
        });
        throw new Error(getResponseErrorMessage(response, payload));
      }

      appendFrontendLog("info", `${options.event}_succeeded`, options.successMessage, {
        method,
        path,
        status: response.status,
      });

      return payload === null ? (null as unknown as T) : (payload as T);
    } catch (error) {
      appendFrontendLog("error", `${options.event}_threw`, `${options.failureMessage} (network/runtime)`, {
        method,
        path,
        error: getErrorMessage(error),
        errorDetails: normalizeError(error),
      });
      throw error;
    }
  }, [appendFrontendLog]);

  const syncIndicatorsSnapshot = useCallback(async (
    event: string,
    successMessage: string,
    failureMessage: string,
  ) => {
    const indicatorsData = await requestJson<Indicator[]>("/api/indicators", undefined, {
      event,
      successMessage,
      failureMessage,
    });
    setIndicators(normalizeIndicators(indicatorsData));
  }, [appendFrontendLog, requestJson]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      appendFrontendLog("info", "bootstrap_started", "Fetching initial backend state", {
        apiUrl: API,
        wsUrl: WS_URL,
      });

      try {
        const [candidatesData, generatedData, statusData, indicatorsData, backendLogs] = await Promise.all([
          requestJson<ShortsCandidate[]>("/api/shorts/candidates", undefined, {
            event: "bootstrap_candidates",
            successMessage: "Fetched candidate list",
            failureMessage: "Failed to fetch candidate list",
          }),
          requestJson<GeneratedShort[]>("/api/shorts", undefined, {
            event: "bootstrap_generated",
            successMessage: "Fetched generated shorts list",
            failureMessage: "Failed to fetch generated shorts list",
          }),
          requestJson<StreamStatus>("/api/stream/status", undefined, {
            event: "bootstrap_status",
            successMessage: "Fetched stream status",
            failureMessage: "Failed to fetch stream status",
          }),
          requestJson<Indicator[]>("/api/indicators", undefined, {
            event: "bootstrap_indicators",
            successMessage: "Fetched indicator dashboard state",
            failureMessage: "Failed to fetch indicator dashboard state",
          }),
          requestJson<DebugLogEntry[]>("/api/debug/logs?limit=120", undefined, {
            event: "bootstrap_debug_logs",
            successMessage: "Fetched backend debug logs",
            failureMessage: "Failed to fetch backend debug logs",
          }),
        ]);

        if (cancelled) {
          return;
        }

        setCandidates(Array.isArray(candidatesData) ? candidatesData : []);
        setGeneratedShorts(Array.isArray(generatedData) ? generatedData : []);
        setStreamStatus(normalizeStreamStatus(statusData));
        setIndicators(normalizeIndicators(indicatorsData));

        const normalizedBackendLogs = Array.isArray(backendLogs)
          ? backendLogs.map(normalizeDebugLog).filter((entry): entry is DebugLogEntry => entry !== null)
          : [];
        pushDebugLogs(normalizedBackendLogs);

        appendFrontendLog("info", "bootstrap_completed", "Initial backend state ready", {
          candidateCount: Array.isArray(candidatesData) ? candidatesData.length : 0,
          generatedCount: Array.isArray(generatedData) ? generatedData.length : 0,
          backendLogCount: normalizedBackendLogs.length,
        });
      } catch (error) {
        if (!cancelled) {
          appendFrontendLog("error", "bootstrap_failed", "Initial backend bootstrap failed", {
            error: getErrorMessage(error),
          });
        }
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [appendFrontendLog, pushDebugLogs, requestJson]);

  useEffect(() => {
    if (!streamStatus.isLive) {
      return;
    }

    const timer = window.setInterval(() => {
      setStreamStatus((current) => {
        if (!current.isLive) {
          return current;
        }
        return { ...current, elapsed: current.elapsed + 1 };
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [streamStatus.isLive]);

  const handleWsMessage = useCallback((type: string, data: JsonRecord) => {
    if (type === "debug_log") {
      const logEntry = normalizeDebugLog(data);
      if (logEntry) {
        pushDebugLogs([logEntry]);
      }
      return;
    }

    appendFrontendLog("debug", `ws_${type}`, `Received WS event: ${type}`, summarizePayload(data));

    switch (type) {
      case "candidate_created":
        setCandidates((current) => {
          const createdCandidate = data as unknown as ShortsCandidate;
          if (current.some((candidate) => candidate.id === createdCandidate.id)) {
            return current;
          }
          return [createdCandidate, ...current];
        });
        break;
      case "candidate_updated": {
        const updatedCandidate = data as unknown as ShortsCandidate;
        setCandidates((current) =>
          current.map((candidate) =>
            candidate.id === updatedCandidate.id ? updatedCandidate : candidate,
          ),
        );
        break;
      }
      case "candidate_deleted":
        setCandidates((current) => current.filter((candidate) => candidate.id !== (data as { id: string }).id));
        break;
      case "generate_progress":
        setCandidates((current) =>
          current.map((candidate) =>
            candidate.id === (data as { candidateId: string }).candidateId
              ? { ...candidate, progress: (data as { percent: number }).percent, status: "generating" }
              : candidate,
          ),
        );
        break;
      case "generate_complete": {
        const generatedShort = (data as { generatedShort?: GeneratedShort }).generatedShort;
        if (generatedShort) {
          setGeneratedShorts((current) => {
            if (current.some((entry) => entry.id === generatedShort.id)) {
              return current;
            }
            return [...current, generatedShort];
          });
        }
        break;
      }
      case "generate_failed": {
        const payload = data as { candidateId?: string; error?: string; jobId?: string };
        const errorMsg = payload.error ?? "Unknown generation error";
        appendFrontendLog("error", "generate_failed", errorMsg, {
          candidateId: payload.candidateId ?? null,
          jobId: payload.jobId ?? null,
        });
        break;
      }
      case "transcript_update":
        setTranscriptLines((current) => limitItems([...current, data as unknown as TranscriptLine], MAX_TRANSCRIPT_LINES));
        break;
      case "indicator_update": {
        const update = data as { type: string; value: number; active: boolean };
        setIndicators((current) =>
          current.map((indicator) =>
            indicator.type === update.type
              ? {
                ...indicator,
                value: typeof update.value === "number" ? update.value : indicator.value,
                active: typeof update.active === "boolean" ? update.active : indicator.active,
              }
              : indicator,
          ),
        );
        break;
      }
      case "stream_status": {
        const status = normalizeStreamStatus(data);
        syncStreamStatus(status);
        if (status.sttAvailable === false) {
          const record = data as Record<string, unknown>;
          const warning = typeof record.warning === "string" ? record.warning : "STT unavailable — transcription disabled";
          appendFrontendLog("warning", "stt_unavailable", warning);
        }
        break;
      }
      case "segment_ready":
        setStreamStatus((current) => ({ ...current, segmentCount: current.segmentCount + 1 }));
        break;
      default:
        appendFrontendLog("warning", "ws_unhandled", `Unhandled WS event type: ${type}`, summarizePayload(data));
        break;
    }
  }, [appendFrontendLog, pushDebugLogs, syncStreamStatus]);

  const syncCandidatesAndShorts = useCallback(async () => {
    try {
      const [candidatesData, generatedData] = await Promise.all([
        requestJson<ShortsCandidate[]>("/api/shorts/candidates", undefined, {
          event: "resync_candidates",
          successMessage: "Re-synced candidates after reconnect",
          failureMessage: "Failed to re-sync candidates",
        }),
        requestJson<GeneratedShort[]>("/api/shorts", undefined, {
          event: "resync_generated",
          successMessage: "Re-synced generated shorts after reconnect",
          failureMessage: "Failed to re-sync generated shorts",
        }),
      ]);
      setCandidates(Array.isArray(candidatesData) ? candidatesData : []);
      setGeneratedShorts(Array.isArray(generatedData) ? generatedData : []);
    } catch {
      // logged by requestJson
    }
  }, [requestJson]);

  useEffect(() => {
    let reconnectTimer: number | undefined;
    let disposed = false;

    function connect() {
      appendFrontendLog("info", "ws_connecting", "Connecting to backend WebSocket", {
        url: WS_URL,
        attempt: reconnectRef.current + 1,
      });

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        const isReconnect = reconnectRef.current > 0;
        reconnectRef.current = 0;
        setWsConnected(true);
        appendFrontendLog("info", "ws_connected", "WebSocket connection established", {
          url: WS_URL,
          isReconnect,
        });
        void syncIndicatorsSnapshot(
          "indicators_resync",
          "Re-synced indicator dashboard after WebSocket connect",
          "Failed to re-sync indicator dashboard after WebSocket connect",
        ).catch(() => {});
        if (isReconnect) {
          void syncCandidatesAndShorts();
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as { type?: string; data?: JsonRecord };
          if (!message.type || !message.data) {
            appendFrontendLog("warning", "ws_invalid_message", "Received malformed WS payload", {
              payload: event.data,
            });
            return;
          }
          handleWsMessage(message.type, message.data);
        } catch (error) {
          appendFrontendLog("warning", "ws_parse_failed", "Failed to parse WS payload", {
            error: getErrorMessage(error),
          });
        }
      };

      ws.onerror = () => {
        appendFrontendLog("warning", "ws_error", "WebSocket reported an error", {
          readyState: ws.readyState,
        });
      };

      ws.onclose = (event) => {
        setWsConnected(false);
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
        if (disposed) {
          return;
        }

        const delay = Math.min(1000 * Math.pow(2, reconnectRef.current), 30000);
        reconnectRef.current += 1;
        appendFrontendLog("warning", "ws_disconnected", "WebSocket disconnected; scheduling reconnect", {
          code: event.code,
          reason: event.reason || "no reason",
          reconnectInMs: delay,
          nextAttempt: reconnectRef.current + 1,
        });
        reconnectTimer = window.setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer);
      }
      wsRef.current?.close();
      wsRef.current = null;
      setWsConnected(false);
    };
  }, [appendFrontendLog, handleWsMessage, syncCandidatesAndShorts, syncIndicatorsSnapshot]);

  const updateCandidateStatus = useCallback(async (id: string, status: ShortsCandidate["status"]) => {
    const normalizedId = id.trim();
    if (!normalizedId) {
      appendFrontendLog("error", "candidate_update_invalid_id", "Cannot update candidate with empty id");
      return;
    }

    const updated = await requestJson<ShortsCandidate | null>(`/api/shorts/candidates/${encodeURIComponent(normalizedId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }, {
      event: `candidate_${status}`,
      successMessage: `Updated candidate to ${status}`,
      failureMessage: `Failed to update candidate to ${status}`,
    });

    setCandidates((current) =>
      current.map((candidate) => {
        if (candidate.id !== normalizedId) {
          return candidate;
        }
        if (!isShortsCandidate(updated)) {
          return { ...candidate, status };
        }
        return updated;
      }),
    );
  }, [requestJson]);

  const confirmCandidate = useCallback(async (id: string) => {
    await updateCandidateStatus(id, "confirmed");
  }, [updateCandidateStatus]);

  const dismissCandidate = useCallback(async (id: string) => {
    await updateCandidateStatus(id, "dismissed");
  }, [updateCandidateStatus]);

  const undoCandidate = useCallback(async (id: string) => {
    await updateCandidateStatus(id, "pending");
  }, [updateCandidateStatus]);

  const generateShorts = useCallback(async (candidateId: string) => {
    appendFrontendLog("info", "generate_batch_started", "Starting generation for all templates", {
      candidateId,
      templateCount: 3,
    });

    const templates = ["blur_fill", "letterbox", "cam_split"] as const;
    for (const template of templates) {
      await requestJson<{ jobId: string; status: string }>("/api/shorts/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidateId, template }),
      }, {
        event: `generate_${template}`,
        successMessage: `Queued generation job for ${template}`,
        failureMessage: `Failed to queue generation job for ${template}`,
      });
    }
  }, [appendFrontendLog, requestJson]);

  const createCandidate = useCallback(async (candidate: CandidateCreateInput) => {
    const payload = {
      ...candidate,
      status: candidate.status ?? "pending",
    };

    const created = await requestJson<ShortsCandidate>("/api/shorts/candidates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }, {
      event: "candidate_created",
      successMessage: "Created new candidate",
      failureMessage: "Failed to create candidate",
    });

    setCandidates((current) => (
      current.some((entry) => entry.id === created.id)
        ? current
        : [created, ...current]
    ));

    return created;
  }, [requestJson]);

  return {
    candidates,
    setCandidates,
    generatedShorts,
    transcriptLines,
    indicators,
    isLive: streamStatus.isLive,
    streamStatus,
    wsConnected,
    debugLogs,
    confirmCandidate,
    dismissCandidate,
    undoCandidate,
    createCandidate,
    generateShorts,
  };
}
