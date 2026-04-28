from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CollectedItem:
    source_name: str
    source_url: str
    title: str
    url: str
    raw_text: str
    published_at: Optional[datetime] = None
