# TruDayz Business Day Calendar Engine

A production-grade local capture engine designed to serve an interactive date validation dashboard while securely processing and deduplicating inbound lead generation data.

## Core Architecture Features
* **Dual-Layer Storage Engine**: Dynamically switches between an active PostgreSQL backend database instance and an encrypted local flat-file storage layout (`leads.txt`).
* **Deterministic Deduplication**: Implements transactional unique constraints and native local file parsing to block duplicate registration attempts before they touch storage files.
* **Integrated Assets Web Server**: Directly hosts the core web interface on port `8080`, handling background API serialization (`POST /api/capture`) without page reloads.

## Local Execution Environment Matrix
* **Runtime**: Python 3.13+
* **System Layer**: Termux (Android POSIX environment)
* **Core Dependencies**: `psycopg2-binary`, `http.server`, C-Compiler Linkage (`clang`, `postgresql-dev`)

## Quickstart Controls

To launch the local interface and API listener from the repository root:
```bash
python3 server.py
