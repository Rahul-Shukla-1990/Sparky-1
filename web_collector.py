import requests
from bs4 import BeautifulSoup
from app.collectors.base import CollectedItem


DEFAULT_HEADERS = {
    "User-Agent": "MaritimeOSINTAgent/0.2 (+local research; configure contact in deployment)"
}


def collect_static_page(source: dict) -> list[CollectedItem]:
    response = requests.get(source["url"], headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else source["name"]
    text = soup.get_text("\n")
    clean_lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_text = "\n".join(clean_lines[:700])

    return [
        CollectedItem(
            source_name=source["name"],
            source_url=source["url"],
            title=title,
            url=source["url"],
            raw_text=clean_text,
            published_at=None,
        )
    ]
