from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password
from app.services.source_loader import sync_sources_to_db


def ensure_default_users(db):
    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(username="admin", display_name="Local Administrator", role="Admin", password_hash=hash_password("admin123"), is_active=True))
        print("Created default admin user: admin / admin123")
    if not db.query(User).filter(User.username == "viewer").first():
        db.add(User(username="viewer", display_name="Local Viewer", role="Viewer", password_hash=hash_password("viewer123"), is_active=True))
        print("Created default viewer user: viewer / viewer123")
    db.commit()


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_users(db)
        count = sync_sources_to_db(db)
        print(f"Database initialized. Sources synced: {count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
