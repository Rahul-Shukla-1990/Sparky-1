# Maritime OSINT Agent v0.4 - Setup Guide

## 1. Purpose

This guide explains how to install, run and operate the Maritime OSINT Agent in local-first mode. The system is designed for no-cost operation using open-source components, local storage, public open sources and Telegram polling.

## 2. Recommended First Installation

Use a Windows or Linux machine that can remain powered on during collection periods. For LAN access, keep the machine connected to the same network as other users.

## 3. Windows Installation

1. Install Python 3.11 or later.
2. Unzip the software package.
3. Open Command Prompt in the folder.
4. Run:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

5. Open `http://127.0.0.1:8000`.
6. Login with `admin / admin123`.

## 4. LAN Sharing

Run:

```bat
scripts\run_lan_windows.bat
```

Find the server IP using:

```bat
ipconfig
```

Other users open `http://SERVER-IP:8000`.

## 5. Telegram Group Intake

Create a Telegram bot through BotFather. Add it to a group. Keep privacy mode enabled. Add the token in `.env`:

```text
TELEGRAM_POLLING_ENABLED="true"
TELEGRAM_BOT_TOKEN="your_token_here"
```

Users submit:

```text
/submit Suspicious skiff approach reported off Somalia https://example.com/post
```

## 6. Roles

Admin manages system settings and audit. Analyst reviews, edits, comments, deletes and exports. Collector submits reports. Viewer only views.

## 7. Incident Handling

Use the incident card to review, move category, add comments, edit comments, or delete incorrect entries. Every major action is written to the audit log.

## 8. Security Notes

Do not store X/Facebook passwords. Do not expose the app directly to the internet. Use VPN or LAN for shared use.
