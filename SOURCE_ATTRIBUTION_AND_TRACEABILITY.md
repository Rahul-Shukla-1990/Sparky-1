# Source Attribution and Contributor Traceability — v0.6

## Purpose

Every incident and submitted item must clearly show where it came from. This is essential for maritime OSINT because source origin affects reliability, urgency, evidentiary value and review priority.

## What v0.6 Adds

Each incident can now carry the following provenance fields:

| Field | Meaning |
|---|---|
| source_channel | background_source, manual_dashboard, telegram_group |
| source_platform | X.com, Facebook, Telegram, Manual, GDELT, RSS, etc. |
| source_display | Human-readable source label |
| submitted_by | Person or Telegram user who shared the item |
| submitted_by_user_id | Local user ID or Telegram user ID |
| source_chat_or_group | Telegram group or source group name |
| source_message_id | Telegram message ID where available |
| source_url | Original URL |

## Dashboard Behaviour

The incident card now shows a Source block with:

- Source
- Channel
- Shared by
- Telegram group
- Telegram message ID
- Original link

## Telegram Behaviour

For Telegram group intake, the system records:

- Telegram username or first name
- Telegram user ID
- Telegram group title
- Telegram chat ID
- Telegram message ID
- Original message text
- Extracted URL, if present

## Exports and Briefs

CSV/JSON exports and daily briefs now include source-provenance fields. This allows downstream analysts to filter items by contributor, group, platform or source channel.

## Operational Benefit

Analysts can quickly distinguish between:

1. automatically collected public-source items,
2. manual dashboard submissions,
3. Telegram group submissions,
4. who shared the social-media lead,
5. whether a link came from X/Facebook/Telegram/news or another platform.
