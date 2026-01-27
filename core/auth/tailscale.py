"""Tailscale whois-based authentication for Zane."""

import json
import logging
import subprocess
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


def is_localhost(remote_addr: str) -> bool:
    """Check if the request is from localhost (dev bypass)."""
    return remote_addr in ("127.0.0.1", "::1", "localhost")


@lru_cache(maxsize=256)
def _whois_cached(addr_port: str) -> Optional[dict]:
    """Call `tailscale whois --json <ip>:<port>` and cache the result."""
    try:
        result = subprocess.run(
            ["tailscale", "whois", "--json", addr_port],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode != 0:
            logger.warning("tailscale whois failed for %s: %s", addr_port, result.stderr.strip())
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("tailscale whois timed out for %s", addr_port)
        return None
    except Exception as e:
        logger.warning("tailscale whois error for %s: %s", addr_port, e)
        return None


def get_user_info(whois_data: dict) -> dict:
    """Extract user info from whois response."""
    user_profile = whois_data.get("UserProfile", {})
    node = whois_data.get("Node", {})
    return {
        "login_name": user_profile.get("LoginName", "unknown"),
        "display_name": user_profile.get("DisplayName", "unknown"),
        "node_name": node.get("Name", "unknown"),
    }


class TailscaleAuth:
    """Tailscale authentication helper."""

    def verify_tailnet_request(self, remote_addr: str, remote_port: int) -> tuple[bool, Optional[dict]]:
        """Verify a request comes from the tailnet.

        Returns:
            (is_authorized, whois_data) — localhost always authorized with None data.
        """
        if is_localhost(remote_addr):
            return True, None

        whois_data = _whois_cached(f"{remote_addr}:{remote_port}")
        if whois_data is None:
            return False, None

        return True, whois_data
