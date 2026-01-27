# Tailscale Authentication Integration

**Date**: 2026-01-27

## Problem
Zane was only accessible from localhost. No way to securely access it from other devices on the tailnet.

## Solution
Added Tailscale whois-based authentication middleware:
- `core/auth/tailscale.py` — LRU-cached `tailscale whois` calls, localhost bypass
- `core/auth/middleware.py` — FastAPI middleware that gates all non-exempt paths
- `main.py` — Dynamic CORS origins from `tailscale ip -4`, conditional middleware via `TAILSCALE_AUTH_ENABLED` env var
- `ui/vite.config.ts` — Bound to `0.0.0.0`, hostname-agnostic SW caching pattern
- Chat endpoint logs Tailscale user identity in transparency logs

## Why It Matters
Enables secure multi-device access to Zane over Tailscale without exposing the service to the public internet. Localhost dev mode is unaffected.
