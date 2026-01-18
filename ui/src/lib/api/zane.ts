import type { ZaneResponse, ChatRequest } from '../types';

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
}

/**
 * Helper to generate unique message IDs
 */
export function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}
