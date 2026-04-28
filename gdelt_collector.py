from urllib.parse import urlencode
import requests
from app.collectors.base import CollectedItem

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def collect_gdelt_query(source: dict) -> list[CollectedItem]:
    query = source.get("query") or "maritime incident Indian Ocean"
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": 50,
        "sort": "datedesc",
    }
    url = f"{GDELT_DOC_API}?{urlencode(params)}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    items: list[CollectedItem] = []
    for article in data.get("articles", []):
        title = article.get("title") or "Untitled GDELT article"
        link = article.get("url") or ""
        domain = article.get("domain") or "GDELT"
        seendate = article.get("seendate") or ""
        language = article.get("language") or ""
        text = f"{title}\n\nSource domain: {domain}\nSeen date: {seendate}\nLanguage: {language}\nURL: {link}"

        items.append(
            CollectedItem(
                source_name=source["name"],
                source_url=url,
                title=title,
                url=link,
                raw_text=text,
                published_at=None,
            )
        )

    return items
