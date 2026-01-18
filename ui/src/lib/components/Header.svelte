<script lang="ts">
  import ColorPicker from './ColorPicker.svelte';
  import { messagesStore } from '../stores/messages';

  let showSettings = false;

  function toggleSettings() {
    showSettings = !showSettings;
  }

  function handleNewChat() {
    messagesStore.newConversation();
  }
</script>

<header class="header">
  <div class="header-left">
    <h1 class="title">Zane</h1>
    <span class="subtitle">Exocortex</span>
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
    align-items: baseline;
    gap: var(--spacing-sm);
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

  .icon-btn:hover {
    background-color: var(--color-bg-secondary);
    color: var(--color-text-primary);
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
