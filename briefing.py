from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Incident, ExportRecord


def generate_daily_brief(db: Session, days: int = 1) -> str:
    brief_dir = Path(settings.brief_dir)
    brief_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    incidents = (
        db.query(Incident)
        .filter(Incident.detected_at >= start)
        .filter(Incident.duplicate_of_id.is_(None))
        .order_by(Incident.alert_level.asc(), Incident.detected_at.desc())
        .all()
    )

    category_counts = Counter(i.category for i in incidents)
    alert_counts = Counter(i.alert_level for i in incidents)
    region_counts = Counter(i.region or "Unknown" for i in incidents)

    path = brief_dir / f"daily_maritime_security_brief_{now.strftime('%Y%m%d_%H%M%S')}.md"

    lines = []
    lines.append("# Daily Maritime Security Brief")
    lines.append("")
    lines.append(f"Generated: {now.isoformat()}")
    lines.append(f"Coverage window: Last {days} day(s)")
    lines.append("")
    lines.append("## Executive Overview")
    lines.append("")
    lines.append(f"Total incident candidates captured: **{len(incidents)}**")
    lines.append("")
    lines.append("### Alert-Level Distribution")
    lines.append("")
    for k, v in alert_counts.items():
        lines.append(f"- {k}: {v}")
    if not alert_counts:
        lines.append("- No incident candidates in this period.")
    lines.append("")
    lines.append("### Category Distribution")
    lines.append("")
    for k, v in category_counts.items():
        lines.append(f"- {k}: {v}")
    if not category_counts:
        lines.append("- No category data available.")
    lines.append("")
    lines.append("### Region Distribution")
    lines.append("")
    for k, v in region_counts.most_common(10):
        lines.append(f"- {k}: {v}")
    if not region_counts:
        lines.append("- No region data available.")
    lines.append("")
    lines.append("## High-Priority Incident Candidates")
    lines.append("")

    high_priority = [i for i in incidents if i.alert_level in ["Critical", "High"]]
    if not high_priority:
        lines.append("No Critical or High incident candidates captured in this window.")
    else:
        for inc in high_priority:
            lines.append(f"### {inc.title}")
            lines.append("")
            lines.append(f"- Category: {inc.category}")
            lines.append(f"- Alert Level: {inc.alert_level}")
            lines.append(f"- Confidence: {round(inc.confidence_score, 1)}")
            lines.append(f"- Verification: {inc.verification_status}")
            lines.append(f"- Region: {inc.region or 'Unknown'}")
            lines.append(f"- Source: {inc.source_name or 'Unknown'}")
            lines.append(f"- URL: {inc.source_url or 'Not available'}")
            lines.append("")
            lines.append((inc.summary or "").replace("\n", " ")[:800])
            lines.append("")

    lines.append("## Analyst Review Note")
    lines.append("")
    lines.append("This brief is machine-generated from open-source collection. Items marked as unverified or probable require analyst confirmation before operational use.")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")

    db.add(ExportRecord(export_type="daily_brief_md", file_path=str(path), record_count=len(incidents)))
    db.commit()

    return str(path)
