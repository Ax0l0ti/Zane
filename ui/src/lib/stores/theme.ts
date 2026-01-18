import { writable } from 'svelte/store';
import type { ThemeConfig } from '../types';
import { ACCENT_COLORS } from '../types';

const STORAGE_KEY = 'zane-theme';

function getInitialTheme(): ThemeConfig {
  if (typeof localStorage === 'undefined') {
    return { accentColor: ACCENT_COLORS.blue };
  }

  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      return { accentColor: ACCENT_COLORS.blue };
    }
  }
  return { accentColor: ACCENT_COLORS.blue };
}

function createThemeStore() {
  const { subscribe, set, update } = writable<ThemeConfig>(getInitialTheme());

  return {
    subscribe,
    setAccentColor: (color: string) => {
      update((theme) => {
        const newTheme = { ...theme, accentColor: color };
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(newTheme));
        }
        return newTheme;
      });
    },
    reset: () => {
      const defaultTheme = { accentColor: ACCENT_COLORS.blue };
      set(defaultTheme);
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultTheme));
      }
    }
  };
}

export const themeStore = createThemeStore();
