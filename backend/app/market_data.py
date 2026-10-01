"""Live stock/ETF price lookups via Finnhub (https://finnhub.io). Requires
a free API key, set as the FINNHUB_API_KEY environment variable before
starting the backend - see the README. Only called on demand (a user
clicking "refresh price"), never on a schedule, to stay well within
Finnhub's free-tier rate limit."""

from __future__ import annotations

import os

import httpx

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"


class MarketDataError(Exception):
    pass


def fetch_quote(symbol: str) -> float:
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        raise MarketDataError(
            "FINNHUB_API_KEY is not set - export it in the shell you run the "
            "backend from (see README) to enable price lookups."
        )

    try:
        response = httpx.get(
            FINNHUB_QUOTE_URL, params={"symbol": symbol, "token": api_key}, timeout=5.0
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise MarketDataError(f"Couldn't reach Finnhub: {exc}") from exc

    data = response.json()
    price = data.get("c")
    if not price:
        raise MarketDataError(f"No price returned for symbol '{symbol}' - check it's correct.")
    return float(price)
