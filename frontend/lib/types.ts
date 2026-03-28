export type IndicatorType =
  | "manual"
  | "chat_velocity"
  | "superchat"
  | "audio_spike"
  | "emote_flood"
  | "sentiment_shift"
  | "viewer_spike"
  | "clip_burst"
  | "kill_event"
  | "keyword"
  | "gift_wave"
  | "poll_moment"
  | "overlay_alert";

export interface Indicator {
  id: string;
  type: IndicatorType;
  label: string;
  icon: string;
  value: number; // 0-100
  color: string;
  active: boolean;
}

export interface TranscriptLine {
  id: string;
  timestamp: string;
  text: string;
  speaker?: string;
  isHighlight?: boolean;
}

export interface ShortsCandidate {
  id: string;
  startTime: string;
  endTime: string;
  duration: string;
  thumbnailUrl: string;
  title: string;
  indicators: IndicatorType[];
  confidence: number;
  status: "pending" | "confirmed" | "dismissed" | "generating" | "done";
  progress?: number;
  isManual?: boolean;
  capturedTranscript?: string;
}

export interface GeneratedShort {
  id: string;
  title: string;
  thumbnailUrl: string;
  duration: string;
  createdAt: string;
  indicators: IndicatorType[];
}

export interface TimelineEvent {
  id: string;
  time: number; // seconds from start
  type: IndicatorType;
  intensity: number; // 0-1
}
