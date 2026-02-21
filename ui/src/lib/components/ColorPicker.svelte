<script lang="ts">
  import { themeStore } from '../stores/theme';
  import { ACCENT_COLORS, type AccentColor } from '../types';

  const colors: { name: AccentColor; label: string }[] = [
    { name: 'blue', label: 'Blue' },
    { name: 'cyan', label: 'Cyan' },
    { name: 'green', label: 'Green' },
    { name: 'white', label: 'White' },
    { name: 'pink', label: 'Pink' }
  ];

  function selectColor(colorName: AccentColor) {
    themeStore.setAccentColor(ACCENT_COLORS[colorName]);
  }

  function isSelected(colorName: AccentColor): boolean {
    return $themeStore.accentColor === ACCENT_COLORS[colorName];
  }
</script>

<div class="color-picker">
  <label class="label">Accent Color</label>
  <div class="colors">
    {#each colors as color}
      <button
        class="color-btn"
        class:selected={isSelected(color.name)}
        style="--swatch-color: {ACCENT_COLORS[color.name]}"
        on:click={() => selectColor(color.name)}
        title={color.label}
        aria-label={`Select ${color.label} accent color`}
      >
        {#if isSelected(color.name)}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        {/if}
      </button>
    {/each}
  </div>
</div>

<style>
  .color-picker {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .label {
    font-size: 0.875rem;
    color: var(--color-text-secondary);
  }

  .colors {
    display: flex;
    gap: var(--spacing-sm);
  }

  .color-btn {
    width: 28px;
    height: 28px;
    border-radius: var(--radius-full);
    background-color: var(--swatch-color);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform var(--transition-fast), box-shadow var(--transition-fast);
    color: white;
  }

  .color-btn:hover {
    transform: scale(1.1);
  }

  .color-btn.selected {
    box-shadow: 0 0 0 2px var(--color-bg-primary), 0 0 0 4px var(--swatch-color);
  }
</style>
