import type { ZaneResponse, ChatRequest, RollbackResponse, ThreadResponse, ThreadListResponse } from '../types';

const API_BASE = '/chat';

export class ZaneAPI {
  /**
   * Send a message to Zane and get a response.
   * Uses the Vite proxy in dev mode (/chat -> localhost:8000/chat)
   */
  static async sendMessage(message: string, threadId?: string | null): Promise<ZaneResponse> {
    const request: ChatRequest = {
      message
    };

    if (threadId) {
      request.thread_id = threadId;
    }

    const response = await fetch(API_BASE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error (${response.status}): ${errorText}`);
    }

    return response.json();
  }

  /**
   * Load a full conversation thread by ID.
   */
  static async getThread(threadId: string): Promise<ThreadResponse> {
    const response = await fetch(`/thread/${encodeURIComponent(threadId)}`);
    if (response.status === 404) throw new Error('THREAD_NOT_FOUND');
    if (!response.ok) throw new Error(`API Error (${response.status})`);
    return response.json();
  }

  /**
   * List all conversation threads (lightweight metadata).
   */
  static async listThreads(limit = 50): Promise<ThreadListResponse> {
    const url = limit !== 50 ? `/threads?limit=${limit}` : '/threads';
    const response = await fetch(url);
    if (!response.ok) throw new Error(`API Error (${response.status})`);
    return response.json();
  }

  /**
   * Roll back the last [ZANE] skill commit.
   * Resets to the pre-modification snapshot.
   */
  static async rollback(): Promise<RollbackResponse> {
    const response = await fetch('/rollback', {
      method: 'POST',
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Rollback failed (${response.status}): ${errorText}`);
    }

    return response.json();
  }
  /**
   * Rename a thread's suffix (the human-friendly part after the date prefix).
   */
  static async renameThread(oldId: string, newName: string): Promise<{success: boolean, new_thread_id: string}> {
    const response = await fetch('/thread/rename', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_thread_id: oldId, new_name: newName })
    });
    if (!response.ok) throw new Error(`Rename failed (${response.status})`);
    return response.json();
  }
}

/**
 * Send a message with SSE streaming.
 * Calls onLog for each log event as it arrives, then onComplete with the final response.
 */
export async function sendMessageStream(
  message: string,
  threadId: string | null,
  onLog: (log: LogEvent) => void,
  onComplete: (response: ZaneResponse) => void,
  onError: (error: Error) => void
): Promise<void> {
  const request: ChatRequest = { message };
  if (threadId) {
    request.thread_id = threadId;
  }

  try {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error (${response.status}): ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events (data: {...}\n\n)
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || ''; // Keep incomplete event in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;

        try {
          const jsonStr = line.slice(6); // Remove 'data: ' prefix
          const event = JSON.parse(jsonStr);

          if (event.type === 'log') {
            onLog(event.event as LogEvent);
          } else if (event.type === 'response') {
            onComplete(event as ZaneResponse);
          } else if (event.type === 'error') {
            onError(new Error(event.message));
          }
        } catch {
          // Skip malformed JSON
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error : new Error(String(error)));
  }
}

/**
 * Helper to generate unique message IDs
 */
export function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}
