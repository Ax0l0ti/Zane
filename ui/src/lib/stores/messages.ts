import { writable, derived } from 'svelte/store';
import type { Message } from '../types';

const THREAD_STORAGE_KEY = 'zane-thread-id';

function getStoredThreadId(): string | null {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(THREAD_STORAGE_KEY);
}

function createMessagesStore() {
  const messages = writable<Message[]>([]);
  const threadId = writable<string | null>(getStoredThreadId());

  return {
    messages: {
      subscribe: messages.subscribe,
      add: (message: Message) => {
        messages.update((msgs) => [...msgs, message]);
      },
      clear: () => {
        messages.set([]);
      },
      set: messages.set
    },
    threadId: {
      subscribe: threadId.subscribe,
      set: (id: string | null) => {
        threadId.set(id);
        if (typeof localStorage !== 'undefined') {
          if (id) {
            localStorage.setItem(THREAD_STORAGE_KEY, id);
          } else {
            localStorage.removeItem(THREAD_STORAGE_KEY);
          }
        }
      },
      get: () => {
        let current: string | null = null;
        threadId.subscribe((val) => (current = val))();
        return current;
      }
    },
    // Start a new conversation
    newConversation: () => {
      messages.set([]);
      threadId.set(null);
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(THREAD_STORAGE_KEY);
      }
    }
  };
}

export const messagesStore = createMessagesStore();

// Derived store to check if there are any messages
export const hasMessages = derived(
  messagesStore.messages,
  ($messages) => $messages.length > 0
);
