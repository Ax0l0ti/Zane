<script lang="ts">
  import { afterUpdate, createEventDispatcher } from 'svelte';
  import MessageBubble from './MessageBubble.svelte';
  import type { Message, LogEvent } from '../types';

  const dispatch = createEventDispatcher();

  export let messages: Message[] = [];
  export let isLoading: boolean = false;
  export let isStreaming: boolean = false;
  export let streamingLogs: LogEvent[] = [];
  export let error: string | null = null;

  let container: HTMLDivElement;
  let showAllLogs = false;

  // Auto-scroll to bottom when new messages or logs arrive
  afterUpdate(() => {
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });

  // Get the most recent log for the "current step" display
  $: currentLog = streamingLogs.length > 0 ? streamingLogs[streamingLogs.length - 1] : null;

  // Format log message for display
  function formatLogMessage(log: LogEvent): string {
    if (log.subtype === 'tool_call') {
      const toolName = log.metadata?.tool_name || 'tool';
      return `Calling ${toolName}...`;
    }
    if (log.subtype === 'tool_result') {
      return `Tool returned`;
    }
    if (log.subtype === 'knowledge_read') {
      return log.message;
    }
    if (log.subtype === 'history') {
      return log.message;
    }
    return log.message;
  }

  // Get icon for log type
  function getLogIcon(log: LogEvent): string {
    switch (log.type) {
      case 'tool': return '🔧';
      case 'thought': return '💭';
      case 'file_io': return '📁';
      case 'error': return '⚠️';
      default: return '•';
    }
  }
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

    {#if isLoading || (error && streamingLogs.length > 0)}
      <div class="loading-indicator">
        {#if streamingLogs.length > 0}
          <!-- Live thinking display (or error state with logs) -->
          <div class="thinking-container" class:has-error={error}>
            <div class="thinking-header">
              {#if isLoading}
                <span class="thinking-spinner"></span>
                <span class="thinking-label">Thinking...</span>
              {:else if error}
                <span class="error-icon">⚠️</span>
                <span class="thinking-label error">Error</span>
              {/if}
              <button
                class="toggle-logs"
                on:click={() => showAllLogs = !showAllLogs}
                title={showAllLogs ? 'Collapse logs' : 'Expand logs'}
              >
                {showAllLogs ? '▼' : '▶'} {streamingLogs.length}
              </button>
            </div>

            {#if currentLog && !showAllLogs && !error}
              <div class="current-step">
                <span class="step-icon">{getLogIcon(currentLog)}</span>
                <span class="step-message">{formatLogMessage(currentLog)}</span>
              </div>
            {/if}

            {#if showAllLogs || error}
              <div class="logs-timeline">
                {#each streamingLogs as log, i}
                  <div class="log-entry" class:latest={i === streamingLogs.length - 1 && !error}>
                    <span class="log-icon">{getLogIcon(log)}</span>
                    <span class="log-message">{formatLogMessage(log)}</span>
                  </div>
                {/each}
              </div>
            {/if}

            {#if error}
              <div class="error-message">
                <span class="error-label">Error:</span> {error}
                <button class="error-dismiss" on:click={() => dispatch('dismissError')}>✕</button>
              </div>
            {/if}
          </div>
        {:else if isLoading}
          <!-- Fallback to bouncing dots -->
          <div class="typing-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        {/if}
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

  /* Live thinking display */
  .thinking-container {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    background-color: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    min-width: 200px;
    max-width: 400px;
  }

  .thinking-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 0.875rem;
    color: var(--color-text-secondary);
  }

  .thinking-spinner {
    width: 12px;
    height: 12px;
    border: 2px solid var(--color-accent);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .thinking-label {
    font-weight: 500;
    color: var(--color-accent);
  }

  .toggle-logs {
    margin-left: auto;
    padding: 2px 6px;
    font-size: 0.75rem;
    background: transparent;
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    cursor: pointer;
  }

  .toggle-logs:hover {
    background-color: var(--color-bg-tertiary);
  }

  .current-step {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-xs) 0;
    font-size: 0.8125rem;
    color: var(--color-text-muted);
  }

  .step-icon {
    flex-shrink: 0;
  }

  .step-message {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .logs-timeline {
    display: flex;
    flex-direction: column;
    gap: 2px;
    max-height: 200px;
    overflow-y: auto;
    padding: var(--spacing-xs) 0;
    border-top: 1px solid var(--color-border);
  }

  .log-entry {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-xs);
    padding: 2px 0;
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .log-entry.latest {
    color: var(--color-text-secondary);
    font-weight: 500;
  }

  .log-icon {
    flex-shrink: 0;
    font-size: 0.6875rem;
  }

  .log-message {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Error state */
  .thinking-container.has-error {
    border: 1px solid var(--color-error);
    background-color: color-mix(in srgb, var(--color-error), var(--color-bg-secondary) 90%);
  }

  .thinking-label.error {
    color: var(--color-error);
  }

  .error-icon {
    font-size: 0.875rem;
  }

  .error-message {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm);
    margin-top: var(--spacing-xs);
    background-color: color-mix(in srgb, var(--color-error), transparent 85%);
    border-radius: var(--radius-sm);
    font-size: 0.8125rem;
    color: var(--color-error);
    word-break: break-word;
  }

  .error-label {
    font-weight: 600;
    flex-shrink: 0;
  }

  .error-dismiss {
    margin-left: auto;
    flex-shrink: 0;
    padding: 2px 6px;
    font-size: 0.75rem;
    background: transparent;
    border-radius: var(--radius-sm);
    color: var(--color-error);
    cursor: pointer;
    opacity: 0.7;
  }

  .error-dismiss:hover {
    opacity: 1;
    background-color: color-mix(in srgb, var(--color-error), transparent 70%);
  }
</style>
