<script lang="ts">
  import MessageList from './MessageList.svelte';
  import InputArea from './InputArea.svelte';
  import { messagesStore } from '../stores/messages';
  import { chatStore, isLoading, isStreaming, streamingLogs, chatError } from '../stores/chat';
  import { ZaneAPI, generateMessageId, sendMessageStream } from '../api/zane';
  import type { Message, LogEvent } from '../types';

  // Create a reference to the nested store for Svelte's $ syntax
  const messages$ = messagesStore.messages;
  const threadId$ = messagesStore.threadId;

  let loadingThread = true;
  let loadedThreadId: string | null = null;
  let fetchGeneration = 0;  // guards against stale responses from rapid switching

  // Reactive: re-fetch whenever threadId changes (including initial mount)
  $: loadThread($threadId$);

  async function loadThread(id: string | null) {
    const thisGen = ++fetchGeneration;
    if (id === loadedThreadId) return;
    loadedThreadId = id;
    if (!id) {
      loadingThread = false;
      return;
    }
    loadingThread = true;
    try {
      const thread = await ZaneAPI.getThread(id);
      if (thisGen !== fetchGeneration) return; // stale — user switched again
      const restored: Message[] = thread.messages.map((msg, i) => ({
        id: `restored_${i}_${Date.now()}`,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.timestamp)
      }));
      messagesStore.messages.set(restored);
    } catch (err) {
      if (thisGen !== fetchGeneration) return;
      if (err instanceof Error && err.message === 'THREAD_NOT_FOUND') {
        messagesStore.newConversation();
        loadedThreadId = null;
      }
    } finally {
      if (thisGen === fetchGeneration) loadingThread = false;
    }
  }

  async function handleSendMessage(event: CustomEvent<{ message: string }>) {
    const { message } = event.detail;

    if (!message.trim()) return;

    // Add user message immediately
    const userMessage: Message = {
      id: generateMessageId(),
      role: 'user',
      content: message,
      timestamp: new Date()
    };
    messagesStore.messages.add(userMessage);

    // Clear any previous error and start streaming
    chatStore.clearError();
    chatStore.setLoading(true);
    chatStore.setStreaming(true);

    const threadId = messagesStore.threadId.get();

    await sendMessageStream(
      message,
      threadId,
      // onLog: called for each log event as it streams in
      (log: LogEvent) => {
        chatStore.addStreamingLog(log);
      },
      // onComplete: called when the final response arrives
      (response) => {
        // Update thread ID if this is a new conversation
        if (response.thread_id && response.thread_id !== threadId) {
          messagesStore.threadId.set(response.thread_id);
        }

        // Add assistant response with all logs
        const assistantMessage: Message = {
          id: generateMessageId(),
          role: 'assistant',
          content: response.text,
          timestamp: new Date(),
          logs: response.logs,
          reasoning: response.reasoning
        };
        messagesStore.messages.add(assistantMessage);

        // Clean up streaming state
        chatStore.setStreaming(false);
        chatStore.setLoading(false);
        chatStore.clearStreamingLogs();
      },
      // onError: called if streaming fails - keep logs visible for debugging
      (error: Error) => {
        chatStore.setError(error.message);
        chatStore.setStreaming(false);
        chatStore.setLoading(false);
        // DON'T clear streaming logs - keep them visible for debugging
      }
    );
  }
</script>

<div class="chat-container">
  {#if loadingThread}
    <div class="loading-thread">Loading conversation...</div>
  {:else}
    <MessageList
      messages={$messages$}
      isLoading={$isLoading}
      isStreaming={$isStreaming}
      streamingLogs={$streamingLogs}
      error={$chatError}
      on:dismissError={() => { chatStore.clearError(); chatStore.clearStreamingLogs(); }}
    />
  {/if}

  {#if $chatError && $streamingLogs.length === 0}
    <!-- Only show banner if no streaming logs (error is shown inline otherwise) -->
    <div class="error-banner">
      <span class="error-icon">⚠</span>
      <span class="error-text">{$chatError}</span>
      <button class="error-dismiss" on:click={() => chatStore.clearError()}>
        ✕
      </button>
    </div>
  {/if}

  <InputArea on:send={handleSendMessage} disabled={$isLoading} />
</div>

<style>
  .chat-container {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0; /* Important for flex overflow */
    gap: var(--spacing-sm);
    padding: var(--spacing-md) 0;
    background-color: var(--color-accent-tint);
  }

  .loading-thread {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    color: var(--color-text-muted);
    font-size: 0.875rem;
  }

  .error-banner {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background-color: color-mix(in srgb, var(--color-error), transparent 85%);
    border: 1px solid var(--color-error);
    border-radius: var(--radius-md);
    color: var(--color-error);
    font-size: 0.875rem;
  }

  .error-icon {
    flex-shrink: 0;
  }

  .error-text {
    flex: 1;
  }

  .error-dismiss {
    flex-shrink: 0;
    padding: var(--spacing-xs);
    border-radius: var(--radius-sm);
    opacity: 0.7;
  }

  .error-dismiss:hover {
    opacity: 1;
    background-color: color-mix(in srgb, var(--color-error), transparent 70%);
  }
</style>
