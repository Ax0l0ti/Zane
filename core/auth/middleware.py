"""FastAPI middleware for Tailscale authentication."""

import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.auth.tailscale import TailscaleAuth, get_user_info

logger = logging.getLogger(__name__)


class TailscaleAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that verifies requests come from the Tailscale network."""

    def __init__(self, app, tailscale_auth: TailscaleAuth, exempt_paths: list[str] | None = None):
        super().__init__(app)
        self.tailscale_auth = tailscale_auth
        self.exempt_paths = exempt_paths or ["/"]

    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Extract client info
        client = request.client
        if client is None:
            return self._forbidden("No client information available")

        remote_addr = client.host
        remote_port = client.port or 0

        is_authorized, whois_data = self.tailscale_auth.verify_tailnet_request(remote_addr, remote_port)

        if not is_authorized:
            logger.warning("Unauthorized request from %s:%s", remote_addr, remote_port)
            return self._forbidden("Access denied. This service is only available over Tailscale.")

        # Attach user info to request state
        if whois_data:
            request.state.tailscale_user = get_user_info(whois_data)
        else:
            request.state.tailscale_user = None

        return await call_next(request)

    @staticmethod
    def _forbidden(message: str) -> Response:
        return Response(
            content=json.dumps({"detail": message}),
            status_code=403,
            media_type="application/json",
        )
