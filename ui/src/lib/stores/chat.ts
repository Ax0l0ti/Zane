import { writable, derived } from 'svelte/store';

interface ChatState {
  isLoading: boolean;
  error: string | null;
}

function createChatStore() {
  const { subscribe, set, update } = writable<ChatState>({
    isLoading: false,
    error: null
  });

  return {
    subscribe,
    setLoading: (loading: boolean) => {
      update((state) => ({ ...state, isLoading: loading }));
    },
    setError: (error: string | null) => {
      update((state) => ({ ...state, error }));
    },
    clearError: () => {
      update((state) => ({ ...state, error: null }));
    },
    reset: () => {
      set({ isLoading: false, error: null });
    }
  };
}

export const chatStore = createChatStore();

// Convenience derived stores
export const isLoading = derived(chatStore, ($chat) => $chat.isLoading);
export const chatError = derived(chatStore, ($chat) => $chat.error);
