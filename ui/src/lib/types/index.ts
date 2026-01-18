// Types matching Zane's API response structure

export interface LogEvent {
  type: 'thought' | 'tool' | 'file_io' | 'error';
  message: string;
  metadata?: Record<string, unknown>;
}

export interface ZaneResponse {
  text: string;
  thread_id: string;
  audio_base64?: string | null;
  logs: LogEvent[];
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  logs?: LogEvent[];
}

export interface ThemeConfig {
  accentColor: string;
}

export type AccentColor = 'blue' | 'cyan' | 'green' | 'purple' | 'orange';

export const ACCENT_COLORS: Record<AccentColor, string> = {
  blue: '#3b82f6',
  cyan: '#06b6d4',
  green: '#22c55e',
  purple: '#8b5cf6',
  orange: '#f97316'
} as const;
