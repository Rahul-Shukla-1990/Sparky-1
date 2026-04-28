from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path

db_path = Path("data/maritime_osint.db")
if db_path.exists():
    db_path.unlink()
    print("Deleted local database.")
else:
    print("No local database found.")
print("Run: python scripts/init_db.py")
