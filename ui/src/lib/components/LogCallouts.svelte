<script lang="ts">
  import type { LogEvent } from '../types';

  export let logs: LogEvent[];
  export let reasoning: string = '';

  let expanded = false;

  const STEP_ICONS: Record<string, string> = {
    thought: '💭',
    tool: '⚡',
    file_io: '📁',
    error: '❌'
  };

  const STEP_COLORS: Record<string, string> = {
    thought: '#8b5cf6',
    tool: '#f97316',
    file_io: '#22c55e',
    error: '#ef4444'
  };

  // Subtypes that add no debug value
  const SKIP_SUBTYPES = new Set(['receive', 'done']);

  function shouldShow(log: LogEvent): boolean {
    if (log.subtype && SKIP_SUBTYPES.has(log.subtype)) return false;
    return true;
  }

  function stepLabel(log: LogEvent): string {
    // Build a concise label from subtype when available
    if (log.subtype === 'intent') return 'Detected intent';
    if (log.subtype === 'mode') return 'Routing';
    if (log.subtype === 'knowledge_read') return 'Knowledge lookup';
    if (log.subtype === 'knowledge_extract') return 'Extracting knowledge';
    if (log.subtype === 'history') return 'Loading history';
    if (log.subtype === 'skill_exec') return 'Skill execution';
    if (log.subtype === 'skill_gen') return 'Generating skill';
    if (log.subtype === 'plan') return 'Planning';
    if (log.subtype === 'approval') return 'Approval';
    if (log.subtype === 'snapshot') return 'Git snapshot';
    if (log.subtype === 'commit') return 'Git commit';
    if (log.subtype === 'tool_call') return 'Tool call';
    if (log.subtype === 'tool_result') return 'Tool result';
    if (log.subtype === 'tools') return 'Preparing tools';
    if (log.subtype === 'tool_loop') return 'Tool loop';
    if (log.subtype === 'write') return 'Writing file';
    if (log.subtype === 'read') return 'Reading file';
    if (log.type === 'error') return 'Error';
    return log.type.charAt(0).toUpperCase() + log.type.slice(1);
  }

  $: steps = logs.filter(shouldShow);
  $: hasErrors = steps.some(s => s.type === 'error');
  $: stepCount = steps.length;
</script>

{#if steps.length > 0}
  <div class="thinking-block" class:has-errors={hasErrors}>
    <button class="thinking-header" on:click={() => expanded = !expanded}>
      <span class="thinking-icon">💭</span>
      <span class="thinking-label">{reasoning ? 'Reasoning' : 'Thinking'}</span>
      <span class="thinking-summary">
        {#if reasoning}
          {reasoning}
          <span class="step-count">({stepCount} steps)</span>
        {:else}
          {stepCount} step{stepCount !== 1 ? 's' : ''}
        {/if}
        {#if hasErrors}
          <span class="error-badge">⚠</span>
        {/if}
      </span>
      <span class="thinking-chevron" class:expanded>›</span>
    </button>

    {#if expanded}
      <div class="thinking-timeline">
        {#each steps as step, i}
          <div class="timeline-step" class:is-error={step.type === 'error'}>
            <div class="step-gutter">
              <span class="step-dot" style="background: {STEP_COLORS[step.type] || '#666'}"></span>
              {#if i < steps.length - 1}
                <span class="step-line"></span>
              {/if}
            </div>
            <div class="step-content">
              <span class="step-label">{stepLabel(step)}</span>
              <span class="step-message">{step.message}</span>
              {#if step.metadata?.entries}
                <ul class="step-entries">
                  {#each step.metadata.entries as entry}
                    <li>{entry}</li>
                  {/each}
                </ul>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .thinking-block {
    background: var(--color-bg-tertiary);
    border-radius: 8px;
    margin-bottom: 6px;
    overflow: hidden;
    border: 1px solid var(--color-border);
  }

  .thinking-block.has-errors {
    border-color: color-mix(in srgb, var(--color-error) 40%, var(--color-border));
  }

  .thinking-header {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 8px 12px;
    border: none;
    background: none;
    cursor: pointer;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    text-align: left;
  }

  .thinking-header:hover {
    background: color-mix(in srgb, var(--color-text-muted) 6%, transparent);
  }

  .thinking-label {
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .thinking-summary {
    opacity: 0.7;
    display: flex;
    align-items: center;
    gap: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-count {
    font-size: 0.72rem;
    opacity: 0.6;
    flex-shrink: 0;
  }

  .error-badge {
    color: var(--color-error);
  }

  .thinking-chevron {
    margin-left: auto;
    transition: transform var(--transition-fast);
    transform: rotate(0deg);
  }

  .thinking-chevron.expanded {
    transform: rotate(90deg);
  }

  /* Timeline */
  .thinking-timeline {
    padding: 0 12px 10px;
  }

  .timeline-step {
    display: flex;
    gap: 10px;
    min-height: 28px;
  }

  .step-gutter {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 12px;
    flex-shrink: 0;
    padding-top: 5px;
  }

  .step-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .step-line {
    width: 1.5px;
    flex: 1;
    background: var(--color-border);
    margin: 2px 0;
  }

  .step-content {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding-bottom: 6px;
    font-size: 0.78rem;
    line-height: 1.4;
  }

  .step-label {
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .step-message {
    color: var(--color-text-muted);
  }

  .is-error .step-label {
    color: var(--color-error);
  }

  .is-error .step-message {
    color: color-mix(in srgb, var(--color-error) 70%, var(--color-text-muted));
  }

  .step-entries {
    margin: 2px 0 0 12px;
    padding: 0;
    list-style: disc;
    color: var(--color-text-muted);
    font-size: 0.75rem;
  }

  .step-entries li {
    padding: 1px 0;
  }
</style>
