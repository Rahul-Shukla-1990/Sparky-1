import requests
from sqlalchemy.orm import Session
from app.config import settings, csv_to_set
from app.models import AppState
from app.services.social_intake import create_social_submission


def _get_state(db: Session, key: str) -> str | None:
    row = db.query(AppState).filter(AppState.key == key).first()
    return row.value if row else None


def _set_state(db: Session, key: str, value: str):
    row = db.query(AppState).filter(AppState.key == key).first()
    if row: row.value = value
    else: db.add(AppState(key=key, value=value))
    db.commit()


def _telegram_api(method: str, params: dict | None = None):
    if not settings.telegram_bot_token: return None
    response = requests.get(f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}", params=params or {}, timeout=30)
    response.raise_for_status(); return response.json()


def _is_allowed(message: dict) -> bool:
    allowed_chats = csv_to_set(settings.telegram_allowed_chat_ids)
    allowed_users = csv_to_set(settings.telegram_allowed_user_ids)
    chat_id = str((message.get("chat") or {}).get("id", ""))
    user_id = str((message.get("from") or {}).get("id", ""))
    return (not allowed_chats or chat_id in allowed_chats) and (not allowed_users or user_id in allowed_users)


def _is_submit_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return t.startswith("/submit") or t.startswith("/ingest")


def _strip_command(text: str) -> str:
    t = (text or "").strip()
    for cmd in ["/submit", "/ingest"]:
        if t.lower().startswith(cmd):
            return t[len(cmd):].strip()
    return t


def poll_telegram_once(db: Session) -> dict:
    if not settings.telegram_bot_token:
        return {"enabled": False, "reason": "TELEGRAM_BOT_TOKEN not set"}
    params = {"timeout": 1, "allowed_updates": '["message"]'}
    offset = _get_state(db, "telegram_update_offset")
    if offset: params["offset"] = int(offset)
    data = _telegram_api("getUpdates", params=params) or {}
    updates = data.get("result", [])
    processed = ignored = 0; max_id = None
    for update in updates:
        max_id = update.get("update_id", max_id)
        msg = update.get("message") or {}
        text = msg.get("text") or msg.get("caption") or ""
        if not text or not _is_allowed(msg) or not _is_submit_command(text):
            ignored += 1; continue
        chat = msg.get("chat") or {}; user = msg.get("from") or {}
        create_social_submission(db, "Telegram", "telegram_group_submission", _strip_command(text), source_reliability="Unverified", telegram_chat_id=str(chat.get("id", "")), telegram_chat_title=chat.get("title") or chat.get("username"), telegram_user_id=str(user.get("id", "")), telegram_username=user.get("username") or user.get("first_name"), telegram_message_id=str(msg.get("message_id", "")))
        processed += 1
    if max_id is not None: _set_state(db, "telegram_update_offset", str(max_id + 1))
    return {"enabled": True, "updates": len(updates), "processed": processed, "ignored": ignored}
