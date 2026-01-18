<script lang="ts">
  import { afterUpdate } from 'svelte';
  import MessageBubble from './MessageBubble.svelte';
  import type { Message } from '../types';

  export let messages: Message[] = [];
  export let isLoading: boolean = false;

  let container: HTMLDivElement;

  // Auto-scroll to bottom when new messages arrive
  afterUpdate(() => {
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });
</script>

<div class="message-list" bind:this={container}>
  {#if messages.length === 0 && !isLoading}
    <div class="empty-state">
      <div class="empty-icon">Z</div>
      <p class="empty-text">Ask Zane anything</p>
      <p class="empty-hint">Your AI exocortex awaits</p>
    </div>
  {:else}
    {#each messages as message (message.id)}
      <MessageBubble {message} />
    {/each}

    {#if isLoading}
      <div class="loading-indicator">
        <div class="typing-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .message-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    padding: var(--spacing-sm) 0;
  }

  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-sm);
    color: var(--color-text-muted);
  }

  .empty-icon {
    font-size: 4rem;
    font-weight: 700;
    color: var(--color-accent);
    opacity: 0.5;
    line-height: 1;
  }

  .empty-text {
    font-size: 1.125rem;
    color: var(--color-text-secondary);
  }

  .empty-hint {
    font-size: 0.875rem;
  }

  .loading-indicator {
    display: flex;
    padding: var(--spacing-md);
  }

  .typing-dots {
    display: flex;
    gap: 4px;
    padding: var(--spacing-sm) var(--spacing-md);
    background-color: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
  }

  .dot {
    width: 8px;
    height: 8px;
    background-color: var(--color-text-muted);
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;
  }

  .dot:nth-child(1) {
    animation-delay: -0.32s;
  }

  .dot:nth-child(2) {
    animation-delay: -0.16s;
  }

  @keyframes bounce {
    0%, 80%, 100% {
      transform: scale(0.8);
      opacity: 0.5;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }
</style>
