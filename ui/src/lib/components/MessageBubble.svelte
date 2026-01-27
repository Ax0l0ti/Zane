<script lang="ts">
  import type { Message } from '../types';
  import { parseMarkdown } from '../utils/markdown';
  import LogCallouts from './LogCallouts.svelte';

  export let message: Message;

  $: isUser = message.role === 'user';
  $: renderedContent = isUser ? message.content : parseMarkdown(message.content);
  $: formattedTime = message.timestamp.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });
</script>

<div class="message" class:user={isUser} class:assistant={!isUser}>
  {#if !isUser && message.logs?.length}
    <LogCallouts logs={message.logs} />
  {/if}
  <div class="bubble">
    {#if isUser}
      <p class="content">{message.content}</p>
    {:else}
      <div class="content markdown-body">
        {@html renderedContent}
      </div>
    {/if}
  </div>
  <span class="timestamp">{formattedTime}</span>
</div>

<style>
  .message {
    display: flex;
    flex-direction: column;
    max-width: 85%;
  }

  .message.user {
    align-self: flex-end;
    align-items: flex-end;
  }

  .message.assistant {
    align-self: flex-start;
    align-items: flex-start;
  }

  .bubble {
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-lg);
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  .user .bubble {
    background-color: var(--color-accent);
    color: white;
    border-bottom-right-radius: var(--radius-sm);
  }

  .assistant .bubble {
    background-color: var(--color-bg-secondary);
    border-bottom-left-radius: var(--radius-sm);
  }

  .content {
    line-height: 1.5;
  }

  .timestamp {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin-top: var(--spacing-xs);
    padding: 0 var(--spacing-xs);
  }

  /* Markdown content styling */
  .markdown-body :global(p) {
    margin: 0;
  }

  .markdown-body :global(p + p) {
    margin-top: var(--spacing-sm);
  }

  .markdown-body :global(pre) {
    margin: var(--spacing-sm) 0;
  }

  .markdown-body :global(ul),
  .markdown-body :global(ol) {
    margin: var(--spacing-sm) 0;
  }

  .markdown-body :global(h1),
  .markdown-body :global(h2),
  .markdown-body :global(h3),
  .markdown-body :global(h4),
  .markdown-body :global(h5),
  .markdown-body :global(h6) {
    margin-top: var(--spacing-md);
    margin-bottom: var(--spacing-sm);
    font-weight: 600;
    line-height: 1.3;
  }

  .markdown-body :global(h1) { font-size: 1.25rem; }
  .markdown-body :global(h2) { font-size: 1.125rem; }
  .markdown-body :global(h3) { font-size: 1rem; }

  .markdown-body :global(table) {
    font-size: 0.875rem;
  }

  .markdown-body :global(a) {
    color: var(--color-accent);
  }

  .user .markdown-body :global(a) {
    color: white;
    text-decoration: underline;
  }
</style>
