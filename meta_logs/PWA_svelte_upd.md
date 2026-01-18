  # Zane PWA + Svelte Chat UI Implementation Plan

  ## Overview

  Build a Progressive Web App chat interface for Zane using Svelte + Vite. Features dark mode with customizable
  accent colors, markdown rendering for rich content, and PWA installability.

  ---

  ## Project Structure

  ```
  Zane/
  └── ui/                          # NEW: Svelte PWA
  ├── public/
  │   ├── manifest.json        # PWA manifest
  │   └── icons/               # App icons (192, 512)
  ├── src/
  │   ├── main.ts              # Entry point
  │   ├── App.svelte           # Root component
  │   ├── app.css              # Global styles + CSS variables
  │   └── lib/
  │       ├── components/      # UI components
  │       │   ├── Header.svelte
  │       │   ├── ChatContainer.svelte
  │       │   ├── MessageList.svelte
  │       │   ├── MessageBubble.svelte
  │       │   ├── InputArea.svelte
  │       │   └── ColorPicker.svelte
  │       ├── stores/          # Svelte stores
  │       │   ├── theme.ts     # Accent color + localStorage
  │       │   ├── messages.ts  # Chat messages + thread_id
  │       │   └── chat.ts      # Loading/error state
  │       ├── api/
  │       │   └── zane.ts      # API client for /chat
  │       ├── types/
  │       │   └── index.ts     # TypeScript interfaces
  │       └── utils/
  │           └── markdown.ts  # Marked + DOMPurify
  ├── index.html
  ├── vite.config.ts           # Proxy + PWA plugin
  ├── svelte.config.js
  ├── tsconfig.json
  └── package.json
  ```

  ---

  ## Files to Modify

  | File | Change |
  |------|--------|
  | `main.py` | Add CORS middleware + static file serving for `ui/dist/` |

  ---

  ## Implementation Phases

  ### Phase 1: Scaffold Project
  1. Create `ui/` directory
  2. Initialize Vite + Svelte + TypeScript
  3. Configure `vite.config.ts` with API proxy and PWA plugin
  4. Install dependencies: `marked`, `dompurify`, `highlight.js`, `vite-plugin-pwa`

  ### Phase 2: Theme System
  1. Create `app.css` with CSS custom properties (dark mode palette)
  2. Implement `themeStore` with localStorage persistence
  3. Build `ColorPicker.svelte` with preset colors (blue, cyan, green, purple, orange)

  ### Phase 3: API Layer
  1. Define TypeScript interfaces matching `ZaneResponse`, `LogEvent`
  2. Implement `zane.ts` API client (`POST /chat`)
  3. Create `messagesStore` (messages + thread_id) and `chatStore` (loading/error)

  ### Phase 4: Core Components
  1. `App.svelte` - Layout, theme initialization
  2. `Header.svelte` - Title + settings button
  3. `InputArea.svelte` - Text input, send button, Enter to send
  4. `MessageBubble.svelte` - User vs assistant styling, markdown rendering
  5. `MessageList.svelte` - Scrollable container, auto-scroll on new message
  6. `ChatContainer.svelte` - Orchestrates chat flow

  ### Phase 5: Rich Content
  1. Configure `marked` with GitHub Flavored Markdown (tables, code blocks)
  2. Add `highlight.js` for syntax highlighting
  3. Sanitize HTML with DOMPurify
  4. Style code blocks, tables, lists

  ### Phase 6: PWA Setup
  1. Create app icons (simple "Z" logo)
  2. Configure `manifest.json` (name, colors, icons)
  3. Service worker via `vite-plugin-pwa` (cache-first for assets, network-first for API)

  ### Phase 7: FastAPI Integration
  1. Add CORS middleware for dev mode (`localhost:5173`)
  2. Mount `ui/dist/` as static files
  3. Add catch-all route to serve `index.html` for SPA routing

  ### Phase 8: Polish
  1. Loading spinner during API calls
  2. Error messages for failed requests
  3. Voice button stub (disabled, "Coming soon")
  4. Mobile-responsive design

  ---

  ## Key Design Decisions

  | Decision | Rationale |
  |----------|-----------|
  | Svelte over React | Smaller bundle, compiles away framework, simpler |
  | Vite | Fast HMR, native ESM, excellent PWA plugin |
  | localStorage for theme | Small data, needs to persist across sessions |
  | Thread ID in localStorage | Resume sessions; full history loads from API |
  | Network-first for `/chat` | Always try fresh data, fallback shows offline message |
  | No SSR | SPA to local API, no SEO needs, simpler deployment |

  ---

  ## Theme System

  ```css
  :root {
  --color-bg-primary: #0f0f0f;
  --color-bg-secondary: #1a1a1a;
  --color-text-primary: #f5f5f5;
  --color-accent: #3b82f6;        /* Dynamically updated */
  --color-accent-hover: #2563eb;
  }
  ```

  **Preset Colors:**
  - Blue (default): `#3b82f6`
  - Cyan: `#06b6d4`
  - Green: `#22c55e`
  - Purple: `#8b5cf6`
  - Orange: `#f97316`

  ---

  ## Dependencies

  ```json
  {
  "dependencies": {
  "marked": "^12.0.0",
  "dompurify": "^3.0.0",
  "highlight.js": "^11.9.0"
  },
  "devDependencies": {
  "@sveltejs/vite-plugin-svelte": "^3.0.0",
  "svelte": "^4.2.0",
  "typescript": "^5.3.0",
  "vite": "^5.0.0",
  "vite-plugin-pwa": "^0.19.0",
  "@types/dompurify": "^3.0.0"
  }
  }
  ```

  ---

  ## Verification Steps

  1. **Dev mode**: Run `npm run dev` in `ui/`, verify hot reload works
  2. **API proxy**: Send message, verify response from FastAPI
  3. **Theme**: Change accent color, refresh, verify persistence
  4. **Markdown**: Send message that triggers markdown response, verify rendering
  5. **PWA**: Build with `npm run build`, serve from FastAPI, verify installable
  6. **Mobile**: Test on phone (localhost or via Tailscale later)
  7. **Offline**: Enable airplane mode, verify cached UI loads

  ---

  ## Out of Scope (Future)

  - Voice-to-text (stub only)
  - Thread history sidebar
  - Log panel (transparency logs)
  - Tailscale configuration