// Types matching Zane's API response structure

export interface LogEvent {
  type: 'thought' | 'tool' | 'file_io' | 'error';
  subtype?: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface ZaneResponse {
  text: string;
  thread_id: string;
  reasoning?: string;
  audio_base64?: string | null;
  logs: LogEvent[];
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
}

export interface RollbackResponse {
  success: boolean;
  message: string;
  rolled_back_commit?: string;
  reset_to?: string;
}

export interface ThreadMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ThreadResponse {
  id: string;
  created_at: string;
  messages: ThreadMessage[];
}

export interface ThreadSummary {
  id: string;
  created_at: string;
  message_count: number;
  preview: string;
}

export interface ThreadListResponse {
  threads: ThreadSummary[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  logs?: LogEvent[];
  reasoning?: string;
}

export interface ThemeConfig {
  accentColor: string;
}

export type AccentColor = 'blue' | 'cyan' | 'green' | 'purple' | 'orange';

export const ACCENT_COLORS: Record<AccentColor, string> = {
  blue: '#3b83f6ee',
  cyan: '#06b5d4df',
  green: '#22c55e',
  pink: '#c51ba9',
  white: '#d6d6d6c0'
} as const;
