from dateutil import parser as date_parser
import feedparser
from app.collectors.base import CollectedItem


def collect_rss(source: dict) -> list[CollectedItem]:
    feed = feedparser.parse(source["url"])
    items: list[CollectedItem] = []

    for entry in feed.entries[:50]:
        title = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or source["url"]
        summary = getattr(entry, "summary", "") or ""

        published_at = None
        for attr in ["published", "updated", "created"]:
            value = getattr(entry, attr, None)
            if value:
                try:
                    published_at = date_parser.parse(value)
                    break
                except Exception:
                    pass

        items.append(
            CollectedItem(
                source_name=source["name"],
                source_url=source["url"],
                title=title,
                url=link,
                raw_text=f"{title}\n\n{summary}",
                published_at=published_at,
            )
        )

    return items
