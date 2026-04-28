from sqlalchemy.orm import Session
from app.models import SocialSubmission, User
from app.nlp.extractor import extract_urls
from app.services.pipeline import create_incident_from_text


def create_social_submission(db: Session, platform: str, input_type: str, submitted_text: str, submitted_url: str | None = None, source_reliability: str = "Unverified", user: User | None = None, telegram_chat_id: str | None = None, telegram_chat_title: str | None = None, telegram_user_id: str | None = None, telegram_username: str | None = None, telegram_message_id: str | None = None):
    urls = extract_urls(submitted_text)
    url = submitted_url or (urls[0] if urls else None)
    sub = SocialSubmission(platform=platform, input_type=input_type, submitted_text=submitted_text, submitted_url=url, submitted_by_user_id=user.id if user else None, submitted_by_username=user.username if user else None, telegram_chat_id=telegram_chat_id, telegram_chat_title=telegram_chat_title, telegram_user_id=telegram_user_id, telegram_username=telegram_username, telegram_message_id=telegram_message_id, source_reliability=source_reliability)
    db.add(sub); db.commit(); db.refresh(sub)
    title = submitted_text.strip().splitlines()[0][:180] if submitted_text.strip() else "User-submitted maritime item"
    inc = create_incident_from_text(db, title, submitted_text, f"{platform} Submission", url, 3, "User Submitted / Broad IOR", social_submission_id=sub.id, base_confidence_boost=-5.0)
    if inc:
        sub.generated_incident_id = inc.id; db.commit(); db.refresh(sub)
    return sub
