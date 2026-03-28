import type {
  Indicator,
  TranscriptLine,
  ShortsCandidate,
  GeneratedShort,
  TimelineEvent,
} from "./types";

export const indicators: Indicator[] = [
  { id: "1", type: "chat_velocity", label: "Chat Velocity", icon: "💬", value: 78, color: "neon-lime", active: true },
  { id: "2", type: "audio_spike", label: "Audio Spike", icon: "🔊", value: 92, color: "neon-red", active: true },
  { id: "3", type: "superchat", label: "Super Chat", icon: "💰", value: 45, color: "neon-amber", active: false },
  { id: "4", type: "emote_flood", label: "Emote Flood", icon: "😂", value: 63, color: "neon-cyan", active: true },
  { id: "5", type: "sentiment_shift", label: "Sentiment", icon: "🔥", value: 81, color: "neon-violet", active: true },
  { id: "6", type: "viewer_spike", label: "Viewer Spike", icon: "👁", value: 34, color: "neon-cyan", active: false },
  { id: "7", type: "kill_event", label: "Kill Event", icon: "🎯", value: 88, color: "neon-red", active: true },
  { id: "8", type: "keyword", label: "Keyword Hit", icon: "🔑", value: 55, color: "neon-lime", active: false },
];

export const transcriptLines: TranscriptLine[] = [
  { id: "t1", timestamp: "01:23:45", text: "자 여기서 한번 가보겠습니다", speaker: "스트리머" },
  { id: "t2", timestamp: "01:23:48", text: "아 이거 진짜 위험한데...", speaker: "스트리머" },
  { id: "t3", timestamp: "01:23:52", text: "와 진짜 미쳤다!!! 3킬!!!", speaker: "스트리머", isHighlight: true },
  { id: "t4", timestamp: "01:23:55", text: "채팅 폭발하고 있네요 여러분", speaker: "스트리머" },
  { id: "t5", timestamp: "01:23:58", text: "이거 진짜 쇼츠감이다", speaker: "스트리머", isHighlight: true },
  { id: "t6", timestamp: "01:24:02", text: "슈퍼챗 감사합니다! 만원 감사합니다!", speaker: "스트리머" },
  { id: "t7", timestamp: "01:24:06", text: "자 다음 라운드 갑시다", speaker: "스트리머" },
  { id: "t8", timestamp: "01:24:10", text: "오 여기 적 있다 조심조심...", speaker: "스트리머" },
  { id: "t9", timestamp: "01:24:14", text: "아아아아 헤드샷!!! 이거 실화냐", speaker: "스트리머", isHighlight: true },
  { id: "t10", timestamp: "01:24:18", text: "채팅 다시 폭발 ㅋㅋㅋ 미친", speaker: "스트리머" },
  { id: "t11", timestamp: "01:24:22", text: "이 구간 진짜 하이라이트다", speaker: "스트리머", isHighlight: true },
  { id: "t12", timestamp: "01:24:26", text: "멤버십 선물 3개 감사합니다!", speaker: "스트리머" },
];

export const shortsCandidates: ShortsCandidate[] = [
  {
    id: "s1",
    startTime: "01:23:50",
    endTime: "01:24:20",
    duration: "0:30",
    thumbnailUrl: "",
    title: "3연킬 + 채팅 폭발 하이라이트",
    indicators: ["kill_event", "chat_velocity", "audio_spike"],
    confidence: 94,
    status: "pending",
  },
  {
    id: "s2",
    startTime: "01:24:12",
    endTime: "01:24:42",
    duration: "0:30",
    thumbnailUrl: "",
    title: "헤드샷 + 슈퍼챗 러시",
    indicators: ["kill_event", "superchat", "emote_flood"],
    confidence: 87,
    status: "generating",
    progress: 65,
  },
  {
    id: "s3",
    startTime: "01:18:30",
    endTime: "01:19:00",
    duration: "0:30",
    thumbnailUrl: "",
    title: "클러치 1v4 역전 장면",
    indicators: ["audio_spike", "sentiment_shift", "chat_velocity"],
    confidence: 91,
    status: "confirmed",
  },
  {
    id: "s4",
    startTime: "01:15:05",
    endTime: "01:15:35",
    duration: "0:30",
    thumbnailUrl: "",
    title: "스나이퍼 롱샷 2연타",
    indicators: ["kill_event", "emote_flood"],
    confidence: 72,
    status: "dismissed",
  },
];

export const generatedShorts: GeneratedShort[] = [
  {
    id: "g1",
    title: "에이스! 5킬 무쌍 클립",
    thumbnailUrl: "",
    duration: "0:28",
    createdAt: "2분 전",
    indicators: ["kill_event", "audio_spike"],
    template: "blur_fill",
    caption: "에이스! 5킬 무쌍 🔥",
  },
  {
    id: "g2",
    title: "에이스! 5킬 무쌍 클립",
    thumbnailUrl: "",
    duration: "0:28",
    createdAt: "2분 전",
    indicators: ["kill_event", "audio_spike"],
    template: "letterbox",
    caption: "에이스! 5킬 무쌍 🔥",
  },
  {
    id: "g3",
    title: "에이스! 5킬 무쌍 클립",
    thumbnailUrl: "",
    duration: "0:28",
    createdAt: "2분 전",
    indicators: ["kill_event", "audio_spike"],
    template: "cam_split",
  },
];

// Deterministic pseudo-random for SSR/client consistency
function seededRandom(seed: number) {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

export const timelineEvents: TimelineEvent[] = Array.from({ length: 80 }, (_, i) => ({
  id: `te${i}`,
  time: i * 60,
  type: indicators[Math.floor(seededRandom(i * 7) * indicators.length)].type,
  intensity: 0.2 + seededRandom(i * 13) * 0.8,
}));
