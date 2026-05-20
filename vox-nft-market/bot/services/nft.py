import re
import aiohttp
import logging

logger = logging.getLogger(__name__)

NFT_LINK_PATTERN = re.compile(
    r"(?:https?://)?t\.me/nft/([A-Za-z0-9_]+-\d+)", re.IGNORECASE
)

FRAGMENT_NFT_URL = "https://fragment.com/gift/{slug}"

GETGEMS_GRAPHQL_URL = "https://api.getgems.io/graphql"


def parse_nft_link(text: str) -> str | None:
    match = NFT_LINK_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def extract_collection_and_number(slug: str) -> tuple[str, str]:
    parts = slug.rsplit("-", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return slug, ""


async def fetch_nft_data_fragment(slug: str) -> dict | None:
    url = f"https://nft.fragment.com/gift/{slug}.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
            url_html = f"https://fragment.com/gift/{slug}"
            async with session.get(url_html, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    return _parse_fragment_html(html, slug)
    except Exception as e:
        logger.error(f"Fragment fetch error for {slug}: {e}")
    return None


def _parse_fragment_html(html: str, slug: str) -> dict | None:
    result = {}
    collection_name, number = extract_collection_and_number(slug)

    owner_match = re.search(r'class="tm-section-header-title"[^>]*>.*?Owner.*?<a[^>]*>@?([^<]+)</a>', html, re.DOTALL)
    if not owner_match:
        owner_match = re.search(r'"owner"[:\s]*"@?([^"]+)"', html)
    result["owner"] = owner_match.group(1).strip() if owner_match else ""

    model_match = re.search(r'"model"[:\s]*"([^"]+)"', html)
    result["model"] = model_match.group(1) if model_match else collection_name

    rarity_match = re.search(r'"rarity"[:\s]*"([^"]+)"', html)
    if not rarity_match:
        rarity_match = re.search(r'(?:rarity|Редкость)[:\s]*([A-Za-zА-Яа-я]+)', html, re.IGNORECASE)
    result["rarity"] = rarity_match.group(1) if rarity_match else "—"

    result["collection"] = _format_collection_name(collection_name)
    result["number"] = number
    result["slug"] = slug

    return result


def _format_collection_name(raw: str) -> str:
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    name = name.replace("_", " ").replace("-", " ")
    return name.title()


async def fetch_nft_page(slug: str) -> dict | None:
    collection_name, number = extract_collection_and_number(slug)
    url = f"https://t.me/nft/{slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15), allow_redirects=True) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    return _parse_tme_nft_page(html, slug)
    except Exception as e:
        logger.error(f"t.me/nft fetch error for {slug}: {e}")
    return None


def _parse_tme_nft_page(html: str, slug: str) -> dict | None:
    collection_name, number = extract_collection_and_number(slug)

    result = {
        "slug": slug,
        "collection": _format_collection_name(collection_name),
        "model": _format_collection_name(collection_name),
        "number": number,
        "rarity": "—",
        "owner": "",
    }

    owner_match = re.search(r'(?:owner|Owner).*?@([A-Za-z0-9_]+)', html, re.DOTALL)
    if owner_match:
        result["owner"] = owner_match.group(1)

    title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
    if title_match:
        title = title_match.group(1)
        result["model"] = title.split("#")[0].strip() if "#" in title else title.strip()

    rarity_match = re.search(r'(?:rarity|Rarity|Редкость)[:\s]*"?([^"<\n]+)', html, re.IGNORECASE)
    if rarity_match:
        result["rarity"] = rarity_match.group(1).strip()

    return result


async def get_nft_info(slug: str) -> dict | None:
    data = await fetch_nft_data_fragment(slug)
    if data and data.get("collection"):
        return data

    data = await fetch_nft_page(slug)
    if data:
        return data

    collection_name, number = extract_collection_and_number(slug)
    return {
        "slug": slug,
        "collection": _format_collection_name(collection_name),
        "model": _format_collection_name(collection_name),
        "number": number,
        "rarity": "—",
        "owner": "",
    }


async def check_nft_owner(slug: str) -> str | None:
    data = await fetch_nft_data_fragment(slug)
    if data and data.get("owner"):
        return data["owner"]

    data = await fetch_nft_page(slug)
    if data and data.get("owner"):
        return data["owner"]

    return None


async def get_nft_floor_price_ton(collection_name: str) -> float | None:
    query = """
    query GetCollectionFloor($name: String!) {
        alphaNftCollectionByName(name: $name) {
            floorPrice
        }
    }
    """
    variables = {"name": collection_name}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GETGEMS_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    collection = data.get("data", {}).get("alphaNftCollectionByName")
                    if collection and collection.get("floorPrice"):
                        return float(collection["floorPrice"]) / 1e9
    except Exception as e:
        logger.error(f"GetGems floor price error: {e}")

    return None


async def get_gift_price_ton(slug: str) -> float | None:
    collection_name, _ = extract_collection_and_number(slug)

    floor = await get_nft_floor_price_ton(collection_name)
    if floor:
        return floor

    variations = [
        collection_name,
        collection_name.lower(),
        re.sub(r"([a-z])([A-Z])", r"\1-\2", collection_name).lower(),
        re.sub(r"([a-z])([A-Z])", r"\1_\2", collection_name).lower(),
    ]
    for name in variations[1:]:
        floor = await get_nft_floor_price_ton(name)
        if floor:
            return floor

    return None
