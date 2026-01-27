<script lang="ts">
  import type { LogEvent } from '../types';

  export let calloutType: 'read' | 'write' | 'thought' | 'tool' | 'error';
  export let title: string;
  export let items: LogEvent[];

  let expanded = calloutType === 'error';

  const CALLOUT_COLORS: Record<string, string> = {
    read: '#3b82f6',
    write: '#22c55e',
    thought: '#8b5cf6',
    tool: '#f97316',
    error: '#ef4444'
  };

  const CALLOUT_ICONS: Record<string, string> = {
    read: '📖',
    write: '✏️',
    thought: '💭',
    tool: '⚡',
    error: '❌'
  };

  $: color = CALLOUT_COLORS[calloutType];
  $: icon = CALLOUT_ICONS[calloutType];
</script>

<div class="callout" style="--callout-color: {color}">
  <button class="callout-header" on:click={() => expanded = !expanded}>
    <span class="callout-icon">{icon}</span>
    <span class="callout-title">{title}</span>
    <span class="callout-count">({items.length})</span>
    <span class="callout-chevron" class:expanded>›</span>
  </button>
  {#if expanded}
    <div class="callout-body">
      {#each items as log}
        <div class="callout-item">{log.message}</div>
        {#if log.metadata?.entries}
          <ul class="callout-entries">
            {#each log.metadata.entries as entry}
              <li>{entry}</li>
            {/each}
          </ul>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<style>
  .callout {
    border-left: 4px solid var(--callout-color);
    background: color-mix(in srgb, var(--callout-color) 8%, transparent);
    border-radius: 4px;
    margin-bottom: 6px;
    font-size: 0.8rem;
    overflow: hidden;
  }

  .callout-header {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 6px 10px;
    border: none;
    background: none;
    cursor: pointer;
    color: var(--color-text-muted, #888);
    font-size: 0.8rem;
    text-align: left;
  }

  .callout-header:hover {
    background: color-mix(in srgb, var(--callout-color) 12%, transparent);
  }

  .callout-title {
    font-weight: 600;
  }

  .callout-count {
    opacity: 0.7;
  }

  .callout-chevron {
    margin-left: auto;
    transition: transform 0.15s ease;
    transform: rotate(0deg);
  }

  .callout-chevron.expanded {
    transform: rotate(90deg);
  }

  .callout-body {
    padding: 4px 10px 8px;
    border-top: 1px solid color-mix(in srgb, var(--callout-color) 15%, transparent);
  }

  .callout-item {
    padding: 2px 0;
    color: var(--color-text-muted, #888);
  }

  .callout-entries {
    margin: 2px 0 4px 16px;
    padding: 0;
    list-style: disc;
    color: var(--color-text-muted, #888);
  }

  .callout-entries li {
    padding: 1px 0;
  }
</style>
