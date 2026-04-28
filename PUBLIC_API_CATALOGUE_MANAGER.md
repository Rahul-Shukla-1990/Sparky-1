# Public API Catalogue Manager — v0.5

## Purpose

The Public API Catalogue Manager uses the `public-apis/public-apis` GitHub repository as a discovery catalogue for additional candidate APIs.

It does not treat the catalogue as a verified maritime incident feed. It helps the Admin identify possible APIs for news, government data, open data, weather, geocoding, transportation, security and environmental enrichment.

## Operating Principle

No API is activated automatically.

The workflow is:

```text
Import Catalogue
        ↓
Score Maritime Utility
        ↓
Display Candidates
        ↓
Admin Review
        ↓
Approve / Reject
        ↓
Approved API becomes a disabled source template
        ↓
Admin later configures connector details and enables it
```

## Candidate Scoring

The module gives higher scores to categories that are likely useful for maritime OSINT:

- Transportation
- News
- Government
- Open Data
- Geocoding
- Weather
- Environment
- Security
- Tracking

It also checks descriptions for maritime-relevant terms such as AIS, vessel, ship, marine, ocean, weather, tracking, pollution and port.

## Important Limits

The public-apis repository is a community catalogue. Entries may change, break, require keys, or become paid. Before enabling an API operationally, verify:

1. Terms of use
2. Authentication requirements
3. Rate limits
4. HTTPS support
5. Data reliability
6. Operational relevance
7. Cost implications

## Free-by-Default Position

Approved candidates are added as disabled sources. This prevents accidental network use, surprise API calls or cost exposure.
