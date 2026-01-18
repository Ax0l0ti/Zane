<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let disabled: boolean = false;

  const dispatch = createEventDispatcher<{ send: { message: string } }>();

  let inputValue = '';
  let textarea: HTMLTextAreaElement;

  function handleSubmit() {
    if (!inputValue.trim() || disabled) return;

    dispatch('send', { message: inputValue.trim() });
    inputValue = '';

    // Reset textarea height
    if (textarea) {
      textarea.style.height = 'auto';
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  function handleInput() {
    // Auto-resize textarea
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }
</script>

<div class="input-area">
  <div class="input-wrapper">
    <textarea
      bind:this={textarea}
      bind:value={inputValue}
      on:keydown={handleKeydown}
      on:input={handleInput}
      placeholder="Message Zane..."
      rows="1"
      {disabled}
      class:disabled
    ></textarea>

    <button
      class="voice-btn"
      disabled
      title="Voice input coming soon"
      aria-label="Voice input (coming soon)"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
    </button>

    <button
      class="send-btn"
      on:click={handleSubmit}
      disabled={!inputValue.trim() || disabled}
      aria-label="Send message"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="22" y1="2" x2="11" y2="13"/>
        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
      </svg>
    </button>
  </div>

  <p class="hint">Press Enter to send, Shift+Enter for new line</p>
</div>

<style>
  .input-area {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    padding-bottom: var(--spacing-sm);
  }

  .input-wrapper {
    display: flex;
    align-items: flex-end;
    gap: var(--spacing-sm);
    background-color: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-sm);
    transition: border-color var(--transition-fast);
  }

  .input-wrapper:focus-within {
    border-color: var(--color-accent);
  }

  textarea {
    flex: 1;
    min-height: 24px;
    max-height: 200px;
    padding: var(--spacing-xs) var(--spacing-sm);
    background: transparent;
    line-height: 1.5;
  }

  textarea::placeholder {
    color: var(--color-text-muted);
  }

  textarea.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .voice-btn,
  .send-btn {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    transition: all var(--transition-fast);
  }

  .voice-btn {
    color: var(--color-text-muted);
    opacity: 0.5;
    cursor: not-allowed;
  }

  .send-btn {
    background-color: var(--color-accent);
    color: white;
  }

  .send-btn:hover:not(:disabled) {
    opacity: 0.9;
    transform: scale(1.05);
  }

  .send-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .hint {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    text-align: center;
  }
</style>
