# System Framework v0.2

## Mission

Continuously collect, classify, store, display and alert on maritime incidents across the Indian Ocean Region and adjoining maritime belt from the Gulf of Guinea to the Philippines Sea.

## Core Modules

1. Source Registry
2. Collection Engine
3. Raw Document Store
4. AOI Filter
5. NLP Classification Layer
6. Incident Store
7. Confidence and Alert Engine
8. Deduplication Engine
9. Analyst Review Workflow
10. Export and Briefing Engine
11. Dashboard and API Layer
12. Scheduler
13. Collection Logs

## Incident Categories

1. Piracy & Armed Robbery
2. Contraband Smuggling
3. IUU Fishing
4. Illegal Human Migration
5. Maritime Incidents
6. Maritime Security Threats
7. Maritime Environmental Pollution
8. Maritime Cyber Security
9. Hybrid Threats to Maritime Security

## AOI Method

v0.2 uses a broad inclusive geographic belt:
- Latitude: 50S to 35N
- Longitude: 25W to 150E

It also uses region-term matching when coordinates are absent. v0.3 should introduce polygon-based AOI handling.

## Review States

- Pending Review
- Reviewed
- Confirmed
- Rejected

## Alert Levels

- Critical
- High
- Medium
- Low
