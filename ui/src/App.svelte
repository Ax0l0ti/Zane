<script lang="ts">
  import Header from './lib/components/Header.svelte';
  import ChatContainer from './lib/components/ChatContainer.svelte';
  import { themeStore } from './lib/stores/theme';
  import { onMount } from 'svelte';

  onMount(() => {
    // Apply accent color from store on mount
    document.documentElement.style.setProperty('--color-accent', $themeStore.accentColor);
  });

  // Reactively update CSS variable when accent changes
  $: if (typeof document !== 'undefined') {
    document.documentElement.style.setProperty('--color-accent', $themeStore.accentColor);
  }
</script>

<main class="app">
  <Header />
  <ChatContainer />
</main>

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 800px;
    margin: 0 auto;
    padding: 0 1rem;
  }
</style>
