# Maritime OSINT Agent — Free Professional Build v0.7

A local-first, zero-licence-cost, small-team maritime OSINT monitoring platform for the Indian Ocean Region and adjoining maritime security belt.

Version 0.4 focuses on operator usability and analyst control.

## New in v0.7

- In-app Help module.
- Search bar and quick filters.
- Admin/Analyst ability to delete incidents permanently.
- Admin/Analyst ability to move incidents to a different category.
- Admin/Analyst ability to edit incident fields.
- Incident comment system.
- Admin/Analyst ability to edit and delete comments, including comments made by others.
- Improved audit logging for edit, delete, category movement and comments.
- Separate setup guide and product brochure included in the package.

## Default Local Account

Username: `admin`  
Password: `admin123`

Change this before operational use.

## Quick Start - Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## LAN Mode

```bat
scripts\run_lan_windows.bat
```

Other users on the same LAN can open:

```text
http://<server-ip-address>:8000
```

Do not expose v0.7 directly to the public internet without hardening.


## v0.7 Addition — Public API Catalogue Manager

v0.7 adds an Admin-controlled API discovery module using the `public-apis/public-apis` GitHub repository as a catalogue reference. APIs are imported as candidates, scored for maritime utility, and kept disabled until an Admin approves them.

This module is for discovery and enrichment only. No API is automatically activated as an operational source.


## v0.7 Addition — Source Attribution and Contributor Traceability

v0.7 makes source provenance explicit for every incident and every submitted input. The dashboard now shows whether an item came from a background source, manual dashboard submission, or Telegram group intake. Telegram submissions display the person who shared the item, the group title, message ID and capture time where available.

This improves auditability, source confidence assessment and analyst review.

## v0.7 Addition — Visual Intelligence Board

Adds per-incident mini-maps, incident clusters, report inclusion flags, attachment/link handling and reporting graphs for Daily, Weekly, Monthly, Half-Yearly and Annual products.
