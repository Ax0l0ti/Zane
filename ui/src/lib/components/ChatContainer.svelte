<script lang="ts">
  import MessageList from './MessageList.svelte';
  import InputArea from './InputArea.svelte';
  import { messagesStore } from '../stores/messages';
  import { chatStore, isLoading, chatError } from '../stores/chat';
  import { ZaneAPI, generateMessageId } from '../api/zane';
  import type { Message } from '../types';

  // Create a reference to the nested store for Svelte's $ syntax
  const messages$ = messagesStore.messages;

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

    // Clear any previous error
    chatStore.clearError();
    chatStore.setLoading(true);

    try {
      const threadId = messagesStore.threadId.get();
      const response = await ZaneAPI.sendMessage(message, threadId);

      // Update thread ID if this is a new conversation
      if (response.thread_id && response.thread_id !== threadId) {
        messagesStore.threadId.set(response.thread_id);
      }

      // Add assistant response
      const assistantMessage: Message = {
        id: generateMessageId(),
        role: 'assistant',
        content: response.text,
        timestamp: new Date(),
        logs: response.logs
      };
      messagesStore.messages.add(assistantMessage);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      chatStore.setError(errorMessage);
    } finally {
      chatStore.setLoading(false);
    }
  }
</script>

<div class="chat-container">
  <MessageList messages={$messages$} isLoading={$isLoading} />

  {#if $chatError}
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
