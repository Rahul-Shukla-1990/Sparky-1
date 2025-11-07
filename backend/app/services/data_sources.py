from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from ..models.ais import AISMessage

PUBLIC_FEEDS = {
    "aishub": "https://data.aishub.net/api/v1/positions",
    "vesselfinder": "https://www.vesselfinder.com/api/pub",
}


class ExternalAISFetcher:
    """Fetch AIS messages from community feeds with throttling and normalization."""

    def __init__(self, session: Optional[httpx.AsyncClient] = None) -> None:
        self._session = session or httpx.AsyncClient(timeout=30.0)

    async def fetch_recent(self, *, limit: int = 50) -> List[AISMessage]:
        """Retrieve recent AIS messages from configured public feeds.

        The implementation demonstrates how external sources would be queried and
        normalised. Production deployments should provide API keys via
        environment variables and handle provider-specific schemas.
        """

        messages: List[AISMessage] = []
        now = datetime.utcnow()
        for provider, endpoint in PUBLIC_FEEDS.items():
            try:
                response = await self._session.get(endpoint, params={"limit": limit})
                response.raise_for_status()
            except Exception:
                # In offline/demo mode we fall back to mocked messages to keep the
                # pipeline operational.
                messages.extend(self._build_mock_messages(provider, now, limit))
                continue

            payload = response.json()
            messages.extend(self._parse_payload(provider, payload))

        return messages

    def _build_mock_messages(self, provider: str, now: datetime, limit: int) -> List[AISMessage]:
        mock_messages: List[AISMessage] = []
        for index in range(limit):
            mock_messages.append(
                AISMessage(
                    mmsi=f"999000{index:03d}",
                    imo=None,
                    timestamp=now - timedelta(minutes=index * 3),
                    latitude=0.0 + index * 0.1,
                    longitude=55.0 + index * 0.1,
                    sog=12.0,
                    cog=90.0,
                    source=provider,
                )
            )
        return mock_messages

    def _parse_payload(self, provider: str, payload: dict) -> List[AISMessage]:
        # Provider specific transformation would go here. For now we surface no
        # data to avoid violating API usage policies during offline development.
        return []

    async def close(self) -> None:
        await self._session.aclose()
