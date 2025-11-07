# Maritime Domain Awareness Platform Specification

## Vision and Scope
Design and implement an interactive maritime domain awareness platform comparable to Windward AI or MarineTraffic/VesselFinder. The system must ingest AIS data from public feeds and MongoDB, persist 20+ years of vessel histories, detect dark and spoofed activities, and visualise analytics over the Indian Ocean Region (IOR) with future scalability to global coverage. The front end should provide a bilingual (English/Hindi) UI with an interface paradigm similar to leading maritime intelligence products.

## Key Objectives
1. **Persistent Vessel Intelligence**: Store, correlate, and analyse historical AIS records for at least 20 years, tracking identity changes across MMSI, IMO, call signs, and names.
2. **Dark Activity Analytics**: Detect gaps in AIS reporting, evaluate travel feasibility, and highlight suspicious behaviour on maps and reports.
3. **Spoofing Detection**: Identify positional and identity spoofing attempts using kinematic, contextual, and cross-source validation.
4. **Indian Ocean Region Focus**: Generate daily analytic summaries for the IOR with the ability to expand coverage.
5. **User Experience**: Deliver an interactive map UI with tote panels, search, timeline playback, and selectable contextual layers (undersea cables, major shipping lanes, EEZs, weather, etc.).
6. **Role-Based Access**: Support Admin, Analyst, and Viewer roles with tailored permissions.
7. **Data Coverage**: Maintain active monitoring for at least 50 vessels at MVP launch with scalability to global fleets.

## System Architecture Overview
### Data Sources
- **MongoDB AIS Collections**: Existing repository of AIS messages accessible via change streams or scheduled extraction.
- **Public AIS APIs (Requirement 1)**:
  - AISHub, VesselFinder, MarineTraffic public/free tiers, ExactEarth snapshots.
  - NOAA/USCG, EMSA, or other governmental archives for historical enrichment.
- **Supplementary Intelligence**:
  - Satellite SAR/Optical detections, coastal radar feeds, port call databases, and RF direction-finding data when available.
  - Public datasets for undersea cables (e.g., TeleGeography), shipping lanes (e.g., IHO S-411), maritime boundaries (Marine Regions), and weather overlays.

### Data Ingestion Layer
- **Collector Microservices** (Python FastAPI workers or Go services) pulling from MongoDB and external APIs, normalising to a canonical schema.
- **Message Queue**: Apache Kafka (or managed equivalents) buffering inbound AIS updates, non-AIS detections, and auxiliary datasets.
- **Data Normalisation**: Standardise fields (timestamp, MMSI, IMO, lat/lon, SOG, COG, heading, navigation status, data source) and enrich with vessel metadata.

### Storage Layer
- **Operational Datastore**: MongoDB with sharded clusters for vessel states, track points, and event logs.
- **Historical Warehouse**: PostgreSQL + TimescaleDB or ClickHouse for 20-year analytics, with columnar storage (Parquet on S3/GCS) for archival queries.
- **Graph/Identity Store**: Neo4j or ArangoDB tracking vessel identity linkages, merges, splits, and suspicious identity chains.

### Analytics & Detection Layer
- **State Engine**: Maintains the latest kinematic state per vessel and estimates feasible motion envelopes.
- **Dark Activity Detector**:
  - Detect reporting gaps exceeding threshold windows per vessel type/region.
  - Perform travel feasibility analysis using haversine distance vs. maximum allowable displacement.
  - Tag suspicious segments with confidence scores and metadata (duration, estimated route, proximity to sensitive areas).
- **Spoofing Detector**:
  - **Positional Spoofing**: Compare reported position with predicted position, radar/SAR detections, and proximity to land (route engine ensures water-only paths). Detect impossible jumps across land or unrealistic speeds/turn rates.
  - **Identity Spoofing**: Cross-reference MMSI/IMO history, vessel dimensions, transmit power, call signs, and port visit history. Flag re-use or duplication of identifiers.
  - **RF/Signal Analysis**: If RF data available, detect identical MMSI transmissions from multiple geolocations simultaneously.
- **Non-AIS Vessel Detector**: Fuse SAR/radar detections and port logs to identify vessels absent from AIS. Maintain alerts and track handoffs when AIS resumes.
- **Daily Analytics Pipeline**: Generate dashboards and reports summarising IOR vessel traffic, dark events, spoofing incidents, and route deviations.

### API & Integration Layer
- **REST/GraphQL API**: Serve vessel search, history retrieval, dark activity events, spoofing alerts, and analytics summaries.
- **WebSocket/SSE**: Real-time updates for live map interactions and collaborative analysis.
- **Authentication/Authorisation**: OAuth2/OpenID Connect with role-based policies (Admin manages users/settings, Analyst accesses analysis tools, Viewer consumes reports/maps).
- **External Integrations**: Hooks for alerting (email/SMS/webhook), export endpoints (GeoJSON, CSV, PDF reports), and interoperability with maritime command systems.

### Frontend Experience
- **Technology**: React + TypeScript with Mapbox GL JS or deck.gl for vector visualisations; i18n support for English/Hindi labels.
- **Layout**:
  - **Map Canvas**: Central map with vessel markers, trails, heat layers, and overlays.
  - **Tote Panels**: Dockable side panels displaying vessel profile, latest AIS data, risk scores, and timeline controls.
  - **Global Search**: MMSI/IMO search box with suggestions and filter options.
  - **Timeline & Playback**: Horizontal time slider enabling historical playback with dark segments highlighted.
  - **Layer Control**: Toggle undersea cables, shipping lanes, EEZs, weather, piracy incidents, etc.
  - **Notifications Drawer**: List of current alerts (dark activities, spoofing, non-AIS detections) with drill-down.
- **Usability Enhancements**:
  - Keyboard shortcuts for analysts.
  - Snapshot and report export for shareable intelligence products.
  - Accessibility compliance (WCAG 2.1) and responsive layout.

### Route & Geospatial Processing
- **Water-Only Routing**: Use maritime routing graphs (OpenSeaMap, CMAP) or custom generated sea-lane networks to ensure computed paths remain over water.
- **Geospatial Services**: Deploy a PostGIS/pgRouting service or Valhalla configured for maritime edges, supporting ETA estimation and corridor analysis.
- **Map Tile Pipeline**: Pre-generate vector tiles for static layers (cables, shipping lanes) using tippecanoe; serve via tile server (Tileserver GL) or Mapbox vector tile service.

### Security & Compliance
- Encrypt data at rest (MongoDB Atlas encryption, S3 SSE) and in transit (TLS everywhere).
- Audit logging for user actions, data access, and alert acknowledgments.
- Retention policies for 20-year data, with tiered storage and lifecycle management.
- Compliance checks for regional regulations (GDPR for EU data, Indian data residency if applicable).

### Scalability & Deployment
- **Containerisation**: Docker images orchestrated with Kubernetes or managed services (EKS/GKE/AKS).
- **CI/CD**: GitHub Actions pipelines for automated tests, security scanning (Snyk/Trivy), and deployments.
- **Observability**: Prometheus, Grafana, and ELK stack for metrics, logs, and tracing; integrate anomaly detection for ingestion failures.
- **Capacity Planning**: Start with ~50 vessels and scale to thousands by horizontal scaling of ingestion and analytics microservices, leveraging partitioned topics and sharded databases.

## Data Model Highlights
- **Vessel Collection**: Latest state per vessel, including identifiers, dimensions, ownership, risk scores.
- **AIS Message Collection**: Time-series records with geospatial indexes.
- **Event Collection**: Dark activity episodes, spoofing incidents, non-AIS detections with references to supporting evidence.
- **Identity Graph**: Node/edge structures linking MMSI, IMO, call signs, names, and hull numbers over time.
- **Layer Metadata**: Catalogue of contextual datasets with versioning and update cadences.

## Workflow Overview
1. **Ingestion**: Collect AIS from MongoDB change streams and public APIs; normalise and push to Kafka.
2. **Processing**: Stream processing (Apache Flink/Spark) updates vessel states, runs dark/spoofing detection, and writes events to MongoDB/TimescaleDB.
3. **Analytics**: Batch jobs produce daily IOR reports, heatmaps, and identity change summaries.
4. **Delivery**: APIs and WebSockets serve data to the web UI; alerts dispatched via configured channels.
5. **User Interaction**: Analysts explore the map, filter by layers, inspect totes, run queries, and export intelligence.

## Implementation Roadmap
1. **Phase 0 – Foundation**
   - Finalise data contracts and access credentials for public AIS feeds.
   - Stand up core infrastructure (Kubernetes cluster, Kafka, MongoDB, TimescaleDB).
   - Implement canonical schema and ingestion services.
2. **Phase 1 – MVP (50 Vessels)**
   - Basic map with live vessel positions and historical playback.
   - Dark activity detection with water-only route feasibility.
   - Search by MMSI/IMO, tote panels with AIS metadata, bilingual labels.
   - Daily IOR summary report.
3. **Phase 2 – Spoofing & Identity Intelligence**
   - Identity graph service linking MMSI/IMO changes over 20-year dataset.
   - Spoofing detection dashboards and alert workflows.
   - Layer controls for undersea cables, shipping lanes, EEZs.
4. **Phase 3 – Advanced Sensors & Scalability**
   - Integrate SAR/radar detections and non-AIS vessel tracking.
   - Global coverage scaling, partitioned data pipelines, and advanced analytics.
   - Enhanced reporting, role-based dashboards, and collaboration features.
5. **Phase 4 – Optimisation & AI Enhancements**
   - Machine learning-assisted risk scoring.
   - Predictive routing, ETA forecasting, and behaviour clustering.
   - Automated summarisation of dark events for analyst review.

## Open Questions & Next Steps
- Confirm availability and licensing for selected public AIS APIs and contextual datasets.
- Define user management requirements (SSO, MFA, audit retention).
- Validate storage strategy for 20-year retention (cost vs. performance trade-offs).
- Detail alert thresholds and scoring models with subject matter experts.
- Prototype UI wireframes inspired by Windward AI/MarineTraffic to gather stakeholder feedback.

This specification consolidates the user’s additional requirements and outlines a blueprint for delivering an enterprise-grade maritime intelligence interface tailored to Indian Ocean monitoring with future global expansion.
