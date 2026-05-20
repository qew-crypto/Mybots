import aiohttp
import logging

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

_cache: dict[str, tuple[float, float]] = {}
CACHE_TTL = 300  # 5 min


async def get_ton_to_rub_rate() -> float | None:
    import time

    cache_key = "ton_rub"
    if cache_key in _cache:
        value, ts = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return value

    try:
        params = {"ids": "the-open-network", "vs_currencies": "rub"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                COINGECKO_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rate = data.get("the-open-network", {}).get("rub")
                    if rate:
                        _cache[cache_key] = (float(rate), time.time())
                        return float(rate)
    except Exception as e:
        logger.error(f"CoinGecko rate fetch error: {e}")

    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params={"symbol": "TONUSDT"}, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    ton_usd = float((await resp.json())["price"])

            async with session.get(
                url, params={"symbol": "USDTRUB"}, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp2:
                if resp2.status == 200:
                    usd_rub = float((await resp2.json())["price"])
                    rate = ton_usd * usd_rub
                    _cache[cache_key] = (rate, __import__("time").time())
                    return rate
    except Exception as e:
        logger.error(f"Binance rate fetch error: {e}")

    if cache_key in _cache:
        return _cache[cache_key][0]

    return None


async def ton_to_rub(amount_ton: float) -> float | None:
    rate = await get_ton_to_rub_rate()
    if rate is None:
        return None
    return round(amount_ton * rate, 2)
