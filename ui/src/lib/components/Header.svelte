<script lang="ts">
  import ColorPicker from './ColorPicker.svelte';
  import ThreadSwitcher from './ThreadSwitcher.svelte';
  import { messagesStore } from '../stores/messages';
  import { ZaneAPI } from '../api/zane';

  // Local alias so Svelte's $-syntax auto-subscribes to the store
  const threadId = messagesStore.threadId;

  let showSettings = false;
  let showThreadSwitcher = false;
  let rollingBack = false;

  // Rename state
  let editing = false;
  let editValue = '';
  let renameError = '';

  /**
   * Extract the date prefix and suffix from a thread ID.
   * e.g. 't_260130_133817_abc' → { prefix: 't_260130', suffix: '133817_abc' }
   *      'thread_20260130_...' → { prefix: 'thread_20260130', suffix: '...' }
   */
  function splitThreadId(id: string): { prefix: string; suffix: string } | null {
    // New format: t_YYMMDD_*
    let m = id.match(/^(t_\d{6})_(.+)$/);
    if (m) return { prefix: m[1], suffix: m[2] };
    // Old format: thread_YYYYMMDD_*
    m = id.match(/^(thread_\d{8})_(.+)$/);
    if (m) return { prefix: m[1], suffix: m[2] };
    return null;
  }

  function startEditing() {
    const id = $threadId;
    if (!id) return;
    const parts = splitThreadId(id);
    if (!parts) return;
    editValue = parts.suffix;
    renameError = '';
    editing = true;
  }

  function cancelEditing() {
    editing = false;
    renameError = '';
  }

  async function commitRename() {
    const id = $threadId;
    if (!id) return;
    // Sanitize: spaces → underscores, strip unsafe chars
    const sanitized = editValue.trim().replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_\-]/g, '');
    if (!sanitized) {
      cancelEditing();
      return;
    }
    const parts = splitThreadId(id);
    if (!parts) return;
    // No change
    if (sanitized === parts.suffix) {
      editing = false;
      return;
    }
    try {
      const result = await ZaneAPI.renameThread(id, sanitized);
      if (result.success) {
        messagesStore.threadId.set(result.new_thread_id);
      }
      editing = false;
      renameError = '';
    } catch (err) {
      renameError = err instanceof Error ? err.message : 'Rename failed';
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      commitRename();
    } else if (e.key === 'Escape') {
      cancelEditing();
    }
  }

  function toggleThreadSwitcher() {
    showThreadSwitcher = !showThreadSwitcher;
  }

  function handleThreadSelect(event: CustomEvent<{ threadId: string }>) {
    const { threadId: newId } = event.detail;
    showThreadSwitcher = false;
    if (newId === $threadId) return;
    messagesStore.messages.clear();
    messagesStore.threadId.set(newId);
  }

  function handleThreadSwitcherClose() {
    showThreadSwitcher = false;
  }

  function toggleSettings() {
    showSettings = !showSettings;
  }

  function handleNewChat() {
    messagesStore.newConversation();
  }

  async function handleRollback() {
    if (!confirm('Roll back the last Zane skill change? This cannot be undone.')) return;

    rollingBack = true;
    try {
      const result = await ZaneAPI.rollback();
      alert(result.message);
    } catch (err) {
      alert(`Rollback error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      rollingBack = false;
    }
  }
</script>

<header class="header">
  <div class="header-left">
    <div class="header-top">
      <h1 class="title">Zane</h1>
      <span class="subtitle">Exocortex</span>
    </div>
    {#if editing}
      {@const parts = $threadId ? splitThreadId($threadId) : null}
      <span class="thread-id thread-edit-row">
        {#if parts}
          <span class="thread-prefix">{parts.prefix}_</span>
        {/if}
        <input
          class="thread-edit-input"
          type="text"
          bind:value={editValue}
          on:keydown={handleKeydown}
          on:blur={commitRename}
          autofocus
        />
        {#if renameError}
          <span class="rename-error">{renameError}</span>
        {/if}
      </span>
    {:else}
      <div class="thread-id-row">
        <button class="thread-id thread-id-btn" on:click={startEditing} title="Click to rename">
          {$threadId ? $threadId : 'New conversation'}
        </button>
        <button
          class="chevron-btn"
          class:open={showThreadSwitcher}
          on:click={toggleThreadSwitcher}
          title="Switch thread"
          aria-label="Open thread list"
        >▼</button>
      </div>
      <ThreadSwitcher
        open={showThreadSwitcher}
        currentThreadId={$threadId}
        on:select={handleThreadSelect}
        on:close={handleThreadSwitcherClose}
      />
    {/if}
  </div>

  <div class="header-right">
    <button
      class="icon-btn"
      on:click={handleNewChat}
      title="New conversation"
      aria-label="Start new conversation"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 5v14M5 12h14"/>
      </svg>
    </button>

    <button
      class="icon-btn"
      on:click={handleRollback}
      disabled={rollingBack}
      title="Rollback last Zane change"
      aria-label="Rollback last skill change"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="1 4 1 10 7 10"/>
        <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
      </svg>
    </button>

    <button
      class="icon-btn"
      class:active={showSettings}
      on:click={toggleSettings}
      title="Settings"
      aria-label="Toggle settings"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
      </svg>
    </button>
  </div>
</header>

{#if showSettings}
  <div class="settings-panel">
    <ColorPicker />
  </div>
{/if}

<style>
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) 0;
    border-bottom: 1px solid var(--color-border);
  }

  .header-left {
    display: flex;
    flex-direction: column;
    gap: 2px;
    position: relative;
  }

  .thread-id-row {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .chevron-btn {
    background: none;
    border: none;
    padding: 0 2px;
    cursor: pointer;
    color: var(--color-text-muted);
    font-size: 0.55rem;
    opacity: 0.5;
    transition: opacity 0.15s, transform 0.15s;
    line-height: 1;
  }

  .chevron-btn:hover {
    opacity: 1;
  }

  .chevron-btn.open {
    opacity: 1;
    transform: rotate(180deg);
  }

  .header-top {
    display: flex;
    align-items: baseline;
    gap: var(--spacing-sm);
  }

  .thread-id {
    font-size: 0.7rem;
    font-family: monospace;
    color: var(--color-text-muted);
    opacity: 0.7;
  }

  .thread-id-btn {
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    text-align: left;
    font: inherit;
    color: inherit;
    opacity: inherit;
  }

  .thread-id-btn:hover {
    opacity: 1;
    text-decoration: underline;
    text-decoration-style: dotted;
  }

  .thread-edit-row {
    display: flex;
    align-items: center;
    gap: 0;
  }

  .thread-prefix {
    opacity: 0.5;
  }

  .thread-edit-input {
    font: inherit;
    font-size: 0.7rem;
    font-family: monospace;
    color: var(--color-text-primary);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-accent);
    border-radius: var(--radius-sm);
    padding: 1px 4px;
    outline: none;
    width: 16ch;
  }

  .rename-error {
    color: var(--color-error);
    font-size: 0.65rem;
    margin-left: var(--spacing-xs);
  }

  .title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-accent);
    letter-spacing: -0.02em;
  }

  .subtitle {
    font-size: 0.875rem;
    color: var(--color-text-muted);
    font-weight: 400;
  }

  .header-right {
    display: flex;
    gap: var(--spacing-sm);
  }

  .icon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    transition: all var(--transition-fast);
  }

  .icon-btn:hover:not(:disabled) {
    background-color: var(--color-bg-secondary);
    color: var(--color-text-primary);
  }

  .icon-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .icon-btn.active {
    background-color: var(--color-accent-light);
    color: var(--color-accent);
  }

  .settings-panel {
    padding: var(--spacing-md) 0;
    border-bottom: 1px solid var(--color-border);
  }
</style>
