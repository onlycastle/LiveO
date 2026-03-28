const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  stream: {
    start: (source: string, url?: string) =>
      request("/api/stream/start", {
        method: "POST",
        body: JSON.stringify({ source, url }),
      }),
    stop: () => request("/api/stream/stop", { method: "POST" }),
    status: () => request<{
      isLive: boolean;
      elapsed: number;
      captureMethod: string;
      error: string | null;
      segmentCount: number;
    }>("/api/stream/status"),
  },

  candidates: {
    list: () => request<import("./types").ShortsCandidate[]>("/api/shorts/candidates"),
    create: (data: Record<string, unknown>) =>
      request<import("./types").ShortsCandidate>("/api/shorts/candidates", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Record<string, unknown>) =>
      request<import("./types").ShortsCandidate>(`/api/shorts/candidates/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/api/shorts/candidates/${id}`, { method: "DELETE" }),
  },

  shorts: {
    list: () => request<import("./types").GeneratedShort[]>("/api/shorts"),
    generate: (data: Record<string, unknown>) =>
      request<{ jobId: string; status: string }>("/api/shorts/generate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  settings: {
    get: () => request<Record<string, unknown>>("/api/settings"),
    update: (data: Record<string, unknown>) =>
      request<Record<string, unknown>>("/api/settings", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },
};

export type WSMessageHandler = (msg: { type: string; data: Record<string, unknown> }) => void;

export function connectWebSocket(onMessage: WSMessageHandler): WebSocket {
  const ws = new WebSocket(`${WS_URL}/ws/events`);
  ws.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      onMessage(parsed);
    } catch {
      // ignore malformed messages
    }
  };
  return ws;
}
