# Zane

**Agentic AI Assistant that Evolves**

Zane is a self-improving, multi-agent AI assistant designed to autonomously expand its own capabilities over time. It operates over Tailscale, enabling access from anywhere (including mobile devices), and uses a development agent to iteratively improve its own codebase.

This is an old iteration and my new one is in private. This focuses on hardcoding skills, the new iteration works around .md skills for more fluidity. This does have better token consumption and latency.

---

## Overview

Zane is built around the idea of **agentic systems that don’t remain static**. Instead of a fixed assistant, Zane continuously evolves by:

- Expanding its own functionality
- Modifying and extending its UI
- Persisting long-term memory
- Iterating on its architecture via a controlled development loop

---

## Features

- **Multi-Agent Architecture**  
  Coordinated agents handle planning, execution, and development tasks.

- **Self-Improving Dev Agent**  
  A dedicated agent that can modify the codebase via Git, enabling iterative capability expansion.

- **Long-Term Memory System**  
  Stores context and learning across sessions to support continuous improvement.

- **Secure Remote Access (Tailscale)**  
  Runs over a mesh VPN, allowing seamless access from mobile devices or remote environments.

- **Modern Frontend (Svelte + TypeScript)**  
  Lightweight, reactive UI that can be extended dynamically by the system itself.

---

## Tech Stack

- **Backend:** Python (agent orchestration)
- **Frontend:** Svelte, TypeScript
- **Networking:** Tailscale (mesh VPN)
- **Environment:** Pixi

---

## Getting Started

### Prerequisites

- [Pixi](https://pixi.sh/)
- Python (managed via Pixi)
- Tailscale installed and configured (for remote access)

---

### Run Zane

```bash
pixi run python dev.py
