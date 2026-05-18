# Ontology Discovery Catalog (Brain Builder)

**Ontology Discovery Catalog** is a specialized search engine and curated library of benchmark industry business models (ontologies, vocabularies, taxonomies, and standards). As a core module of the **Brain Builder** ecosystem, it is designed to rapidly onboard business consultants, system analysts, and AI agents into the domain of a new client (e.g., healthcare clinics, manufacturing plants, retail chains, fintech companies).

---

## 🌟 Key Features

- **Automated Ingestion & Aggregation**: Harvests data from leading global semantic repositories (LOV, W3ID, W3C, Schema.org, GS1, HL7 FHIR, FIBO, etc.).
- **Data Purity (Zero-Shot AI on Ingestion)**: Exclusively stores official texts, descriptions, and structures directly from primary sources, completely eliminating AI hallucinations or distortions during data collection.
- **Advanced Full-Text Search (SQLite FTS5 + BM25)**: Delivers instant search capabilities with built-in support for synonyms, prefix matching, and weighted ranking across titles, descriptions, tags, and domain fields.
- **Multidimensional Faceted Filtering**: Seamlessly filters resources by type, industry, file format (TTL, OWL, JSON-LD, RDF), verification status, geographic region, and coverage scope.
- **On-Demand AI Enrichment**: Enables targeted enrichment of sparse records (generating `short_description`, tags, country/region, and coverage scope) via LLMs (supporting GitHub Models API / Azure Inference) upon explicit user request.
- **Interview Questionnaire Generation**: Transforms complex semantic entities (e.g., `Recipe`, `Batch`, `Observation`, `TradeItem`) into natural, human-friendly interview questions tailored for business stakeholders.

---

## 🏗 Architecture & Project Structure

The project is built on a lightweight, high-performance stack: **FastAPI + SQLite (FTS5) + Vanilla JS/CSS/HTML**.

```
c:\Apps\ont\
├── main.py                     # Main FastAPI server and REST API endpoints
├── parser.py                   # Database initialization and ingestion script (LOV, W3ID, GitHub)
├── setup_fts.py                # Setup script for FTS5 full-text search virtual tables & triggers
├── classify.py                 # Rule-based classification and data normalization script
├── check_quality.py            # Quality scoring utility and database metrics analyzer
├── cleanup.py                  # Database pruning utility to remove sparse or non-semantic records
├── patch.py                    # Database migration script for adding new columns/properties
├── requirements.txt            # Python dependencies (fastapi, uvicorn, requests, etc.)
├── ontology.db                 # SQLite database (automatically generated)
├── static/                     # Web frontend static assets
│   └── index.html              # Single Page Application (SPA) dashboard and catalog UI
├── catalog-quality-guideline.md # Developer guidelines for catalog normalization and quality
└── ontology-discovery-concept.md # Conceptual architecture and business logic documentation
```

---

## 🚀 Quick Start

### 1. Install Dependencies

Ensure Python 3.8+ is installed, then run:

```bash
pip install -r requirements.txt
```

### 2. Initialize Database & Ingest Data

Run the parser to create `ontology.db`, load benchmark standards, and fetch active vocabularies from external APIs (LOV, GitHub/W3ID):

```bash
python parser.py
```

> **Note:** To interact with the GitHub API during W3ID ingestion, the script uses the `GITHUB_TOKEN` environment variable. You can set it before running:
> `export GITHUB_TOKEN="your_personal_access_token"` (Linux/Mac) or `$env:GITHUB_TOKEN="your_personal_access_token"` (Windows PowerShell).

### 3. Setup Full-Text Search (FTS5)

Once the `resources` table is populated, generate the `resources_fts` virtual table for BM25 search ranking:

```bash
python setup_fts.py
```

### 4. Pruning & Classification (Optional)

To remove non-semantic records and execute rule-based normalization (assigning industries, `country_or_region`, and `coverage_scope`):

```bash
python cleanup.py
python classify.py
```

### 5. Start the FastAPI Server

Launch the Uvicorn development server:

```bash
python main.py
```

Alternatively, run via CLI:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Web Application SPA: **http://localhost:8000**  
- Interactive API Documentation (Swagger UI): **http://localhost:8000/docs**

---

## 🛠 Core Scripts Overview

### `main.py`
The primary FastAPI application serving the REST API and static frontend:
- `GET /api/resources` — Retrieves paginated resources with filtering, facet matching, and FTS search.
- `GET /api/filters` — Aggregates facet counts for the sidebar filter UI.
- `POST /api/resources/{id}/enrich` — Triggers an LLM (gpt-4o-mini) to generate a structured `short_description` and tags.
- `GET /` — Serves the frontend SPA (`static/index.html`).

### `parser.py`
Handles initial database seeding and remote fetching:
1. Creates the `resources` table.
2. Inserts 28+ benchmark, high-quality ontologies (`INITIAL_DATA`).
3. Queries the Linked Open Vocabularies (LOV) REST API.
4. Crawls the `perma-id/w3id.org` GitHub repository to extract project READMEs.

### `setup_fts.py`
Creates the SQLite FTS5 virtual table (`resources_fts`), synchronizes it with `resources`, and establishes SQLite triggers (`AFTER INSERT`, `AFTER UPDATE`, `AFTER DELETE`) to keep the search index automatically updated.

### `classify.py`
Performs rule-based classification of existing records using keyword matching across titles and descriptions. Populates `short_description`, `country_or_region` (Global, EU, US, UK, etc.), `coverage_scope` (Universal, Domain-specific, Regional), and `confidence`.

### `check_quality.py`
Analyzes the database to compute the average Quality Score and outputs detailed metrics categorized by status (`verified`, `candidate`, `weak`), file formats, and domain distribution.

### `cleanup.py`
Prunes irrelevant, empty, or non-semantic entries (e.g., W3ID redirects that lack actual ontology files or descriptions), ensuring high relevance across the catalog.

### `patch.py`
Database schema migration script. Dynamically adds new columns (`short_description`, `country_or_region`, `coverage_scope`, `confidence`) if they are missing from older database builds.

---

## 📊 Data Model (SQLite)

The `resources` table contains the following primary fields:
- `id` (TEXT, Primary Key) — Unique identifier (e.g., `schema-org`, `lov-foaf`).
- `title` (TEXT) — Resource title.
- `w3id` (TEXT) — Permanent URI or namespace link.
- `type` (TEXT) — Classification type (`ontology`, `vocabulary`, `taxonomy`, `framework`, `standard`).
- `description` (TEXT) — Full original description from the publisher.
- `short_description` (TEXT) — Concise summary (140-220 characters) for UI cards.
- `domain` (TEXT) — Subject matter / domain area.
- `quality` (REAL) — Calculated Quality Score (0.0 - 1.0).
- `status` (TEXT) — Verification status (`verified`, `candidate`, `weak`).
- `source` (TEXT) — Ingestion source (`schema.org`, `lov`, `w3id.org`, `w3c.org`).
- `questions_hint` (TEXT) — Sample business interview questions for the questionnaire generator.
- `targets`, `formats`, `industry`, `tags`, `entities` (JSON) — JSON arrays of metadata and classes.
- `country_or_region` (TEXT) — Geographic jurisdiction (`Global`, `EU`, `US`, etc.).
- `coverage_scope` (TEXT) — Applicability scope (`Universal`, `Domain-specific`, `Regional`).
- `confidence` (TEXT) — Classification confidence level (`High`, `Medium`, `Low`).

---

## 🔒 Security & API Keys

The project implements Secret Scanning Protection best practices. All external API tokens (e.g., GitHub Personal Access Tokens or Azure AI credentials) are dynamically loaded from environment variables:
```python
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
```
**Never hardcode real credentials or personal access tokens in the source code.**

---

## 📄 License

This project is part of the closed **Brain Builder** ecosystem. All rights to the original ontologies, vocabularies, and standards belong to their respective publishers (W3C, GS1, OMG, ISO, ETSI, etc.).
