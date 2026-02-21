<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { ZaneAPI } from '../api/zane';
  import type { ThreadSummary } from '../types';

  export let open = false;
  export let currentThreadId: string | null = null;

  const dispatch = createEventDispatcher<{
    select: { threadId: string };
    close: void;
  }>();

  let threads: ThreadSummary[] = [];
  let loading = false;
  let error = '';

  // Group threads by date label
  interface ThreadGroup {
    label: string;
    threads: ThreadSummary[];
  }

  function groupByDate(items: ThreadSummary[]): ThreadGroup[] {
    const groups: Map<string, ThreadSummary[]> = new Map();
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);

    for (const thread of items) {
      const date = new Date(thread.created_at);
      const threadDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      let label: string;

      if (threadDay.getTime() === today.getTime()) {
        label = 'Today';
      } else if (threadDay.getTime() === yesterday.getTime()) {
        label = 'Yesterday';
      } else {
        label = threadDay.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }

      if (!groups.has(label)) groups.set(label, []);
      groups.get(label)!.push(thread);
    }

    return Array.from(groups.entries()).map(([label, threads]) => ({ label, threads }));
  }

  async function fetchThreads() {
    loading = true;
    error = '';
    try {
      const result = await ZaneAPI.listThreads();
      threads = result.threads;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load threads';
    } finally {
      loading = false;
    }
  }

  // Fetch fresh list every time dropdown opens
  $: if (open) fetchThreads();

  function handleSelect(threadId: string) {
    dispatch('select', { threadId });
  }

  function handleBackdropClick() {
    dispatch('close');
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      dispatch('close');
    }
  }

  /** Display name: show human-readable suffix or truncated ID */
  function displayName(id: string): string {
    // New format: t_YYMMDD_suffix
    let m = id.match(/^t_\d{6}_(.+)$/);
    if (m) {
      const suffix = m[1];
      // If suffix is hex-like (e.g. 8-char hex from uuid), truncate
      if (/^[0-9a-f]{8,}$/i.test(suffix)) return id.slice(0, 20) + '...';
      return suffix.replace(/_/g, ' ');
    }
    // Old format: thread_YYYYMMDD_suffix
    m = id.match(/^thread_\d{8}_(.+)$/);
    if (m) {
      const suffix = m[1];
      if (/^[0-9a-f]{8,}$/i.test(suffix)) return id.slice(0, 24) + '...';
      return suffix.replace(/_/g, ' ');
    }
    return id;
  }

  $: grouped = groupByDate(threads);
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
  <!-- Transparent backdrop for click-outside -->
  <div class="backdrop" on:click={handleBackdropClick}></div>

  <div class="dropdown" role="listbox" aria-label="Thread list">
    {#if loading}
      <div class="dropdown-status">Loading threads...</div>
    {:else if error}
      <div class="dropdown-status dropdown-error">{error}</div>
    {:else if threads.length === 0}
      <div class="dropdown-status">No conversations yet</div>
    {:else}
      {#each grouped as group}
        <div class="group-label">{group.label}</div>
        {#each group.threads as thread}
          <button
            class="thread-row"
            class:active={thread.id === currentThreadId}
            on:click={() => handleSelect(thread.id)}
            role="option"
            aria-selected={thread.id === currentThreadId}
          >
            <div class="thread-row-name">{displayName(thread.id)}</div>
            <div class="thread-row-meta">
              <span class="thread-row-count">{thread.message_count} msgs</span>
              <span class="thread-row-preview">{thread.preview}</span>
            </div>
          </button>
        {/each}
      {/each}
    {/if}
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 99;
  }

  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 100;
    width: min(360px, calc(100vw - 2rem));
    max-height: 400px;
    overflow-y: auto;
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    margin-top: 4px;
  }

  .dropdown-status {
    padding: 1rem;
    text-align: center;
    color: var(--color-text-muted);
    font-size: 0.8rem;
  }

  .dropdown-error {
    color: var(--color-error);
  }

  .group-label {
    padding: 0.5rem 0.75rem 0.25rem;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    opacity: 0.7;
  }

  .thread-row {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: none;
    border: none;
    border-left: 3px solid transparent;
    cursor: pointer;
    text-align: left;
    color: var(--color-text-secondary);
    font-size: 0.8rem;
    transition: background-color 0.1s;
  }

  .thread-row:hover {
    background: color-mix(in srgb, var(--color-text-primary), transparent 92%);
  }

  .thread-row.active {
    border-left-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent), transparent 90%);
    color: var(--color-text-primary);
  }

  .thread-row-name {
    font-family: monospace;
    font-size: 0.75rem;
    color: var(--color-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .thread-row-meta {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    font-size: 0.7rem;
    color: var(--color-text-muted);
  }

  .thread-row-count {
    flex-shrink: 0;
    opacity: 0.7;
  }

  .thread-row-preview {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
