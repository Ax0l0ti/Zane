import { writable, derived } from 'svelte/store';
import type { LogEvent } from '../types';

interface ChatState {
  isLoading: boolean;
  isStreaming: boolean;
  streamingLogs: LogEvent[];
  error: string | null;
}

function createChatStore() {
  const { subscribe, set, update } = writable<ChatState>({
    isLoading: false,
    isStreaming: false,
    streamingLogs: [],
    error: null
  });

  return {
    subscribe,
    setLoading: (loading: boolean) => {
      update((state) => ({ ...state, isLoading: loading }));
    },
    setStreaming: (streaming: boolean) => {
      update((state) => ({
        ...state,
        isStreaming: streaming,
        streamingLogs: streaming ? [] : state.streamingLogs
      }));
    },
    addStreamingLog: (log: LogEvent) => {
      update((state) => ({
        ...state,
        streamingLogs: [...state.streamingLogs, log]
      }));
    },
    clearStreamingLogs: () => {
      update((state) => ({ ...state, streamingLogs: [] }));
    },
    setError: (error: string | null) => {
      update((state) => ({ ...state, error }));
    },
    clearError: () => {
      update((state) => ({ ...state, error: null }));
    },
    reset: () => {
      set({ isLoading: false, isStreaming: false, streamingLogs: [], error: null });
    }
  };
}

export const chatStore = createChatStore();

// Convenience derived stores
export const isLoading = derived(chatStore, ($chat) => $chat.isLoading);
export const isStreaming = derived(chatStore, ($chat) => $chat.isStreaming);
export const streamingLogs = derived(chatStore, ($chat) => $chat.streamingLogs);
export const chatError = derived(chatStore, ($chat) => $chat.error);
