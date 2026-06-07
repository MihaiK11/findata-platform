# Findata Platform

Financial Data Warehouse with Temporal Data Modeling, FastAPI, MongoDB, Streamlit Analytics Dashboard, Apache Spark Analytics, and MCP-Powered LLM Assistant.

---

# Overview

Findata Platform is a financial data warehouse designed to ingest, store, analyze, and visualize financial market data while preserving full historical provenance through a temporal data model.

The platform supports:

* Financial asset management
* Time-series storage and analytics
* Temporal versioning
* Data provenance tracking
* Interactive dashboards
* Apache Spark aggregation workflows
* Apache Spark ML forecasting
* MCP-based LLM assistant integration

The system follows an append-only architecture where updates and deletions never modify existing records, ensuring complete auditability and historical reconstruction.

---

# Technology Stack

| Layer              | Technology                      |
| ------------------ | ------------------------------- |
| Web UI             | Streamlit                       |
| Charts             | Plotly                          |
| REST API           | FastAPI                         |
| ASGI Server        | Uvicorn                         |
| Database           | MongoDB Atlas                   |
| Async Driver       | Motor                           |
| Data Validation    | Pydantic v2                     |
| HTTP Client        | httpx                           |
| Scheduler          | APScheduler                     |
| Data Sources       | Nasdaq Data Link, Yahoo Finance |
| Analytics          | pandas, NumPy                   |
| Big Data Analytics | Apache Spark                    |
| Machine Learning   | Spark MLlib                     |
| LLM Assistant      | MCP Python SDK                  |
| Claude Integration | Anthropic SDK                   |
| Package Manager    | uv                              |

---

# Architecture

```text
Yahoo Finance / Nasdaq Data Link
                │
                ▼
        Ingestion Pipeline
                │
                ▼
            MongoDB
                │
     ┌──────────┼──────────┐
     ▼          ▼          ▼
 FastAPI    Spark Jobs    MCP Server
     │          │          │
     ▼          ▼          ▼
 Streamlit  Analytics   Claude/LLM
 Dashboard  Forecasting Assistant
```

---

# Temporal Data Model

The platform implements a temporal warehouse architecture.

## Update Rule

Updates never modify existing documents.

Instead:

1. Previous version remains unchanged.
2. New version is inserted.
3. Latest version is determined using `valid_from`.

## Delete Rule

Deletes are implemented using delete-marker records.

Historical data is never physically removed.

## Provenance Tracking

Every record contains:

```text
data_source
data_source_id
valid_from
is_deleted
```

This allows complete reconstruction of historical states.

---

# Database Collections

## assets

Stores asset metadata.

Example:

```json
{
  "symbol": "AAPL",
  "instrument_class": "stock",
  "region": "US",
  "valid_from": "2025-01-01T00:00:00Z",
  "is_deleted": false
}
```

## data_sources

Stores metadata about providers.

Example:

```json
{
  "source_id": "YAHOO_FINANCE",
  "provider": "Yahoo Finance",
  "valid_from": "2025-01-01T00:00:00Z"
}
```

## time_series

Stores OHLCV data.

Example:

```json
{
  "symbol": "AAPL",
  "date": "2025-01-01",
  "open": 200,
  "high": 205,
  "low": 198,
  "close": 203,
  "volume": 1000000
}
```

---

# Indexing Strategy

MongoDB indexes:

```text
assets:
(symbol, valid_from)

data_sources:
(source_id, valid_from)

time_series:
(symbol, data_source_id, date)
(date)
```

---

# Scalability and Partitioning

Current implementation uses compound indexes for efficient retrieval.

For large-scale deployments the system can be extended with:

```text
time_series_2024
time_series_2025
time_series_2026
```

or MongoDB sharding using:

```text
symbol
date
```

as shard keys.

---

# Installation

## Prerequisites

* Python 3.11+
* MongoDB Atlas
* uv
* Java 11+ (required for Apache Spark)

---

## Clone Repository

```powershell
git clone <repository-url>
cd findata-platform
```

---

## Install Dependencies

```powershell
uv sync
```

---

# Environment Variables

Create a `.env` file:

```env
MONGODB_URL=your_mongodb_connection_string
DB_NAME=findata
NASDAQ_API_KEY=your_nasdaq_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

---

# Running the Application

## Start FastAPI

```powershell
uv run uvicorn app.main:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

---

## Start Streamlit Dashboard

Open a second terminal:

```powershell
uv run streamlit run streamlit_app/app.py
```

Dashboard:

```text
http://localhost:8501
```

---

# Data Ingestion

Seed initial metadata:

```powershell
uv run python -m app.db.seed
```

Load financial data:

```powershell
uv run python -m app.ingestion.fetch
```

Load specific symbols:

```powershell
uv run python -m app.ingestion.fetch AAPL MSFT GOOGL
```

Yahoo Finance only:

```powershell
uv run python -m app.ingestion.fetch AAPL MSFT --yahoo-only
```

---

# REST API Endpoints

## Q1 — Current Asset

```http
GET /api/v1/q1/assets/{symbol}
```

Returns latest non-deleted version of an asset.

---

## Q2 — Latest Assets

```http
GET /api/v1/q2/assets
```

Optional filters:

```text
instrument_class
region
```

---

## Q3 — Data Sources

```http
GET /api/v1/q3/data-sources
```

---

## Q4 — Time Series

```http
GET /api/v1/q4/time-series/{symbol}
```

Supports:

```text
start_date
end_date
data_source_id
limit
```

---

## Q5 — Latest Time-Series Snapshot

```http
GET /api/v1/q5/latest-time-series
```

Returns latest observation per symbol.

---

# Analytics

Endpoint:

```http
GET /analytics/{symbol}
```

Computes:

* Moving Averages (5, 20, 50)
* Trend Detection
* Daily Returns
* Volatility
* Mean
* Median
* Standard Deviation
* Linear Forecast

---

# Apache Spark Workflows

The platform includes Spark-based analytics and forecasting.

## Spark Aggregation

Location:

```text
app/spark_jobs/aggregation.py
```

Computes:

* Mean Price
* Minimum Price
* Maximum Price
* Symbol-Level Aggregations

Run:

```powershell
spark-submit app/spark_jobs/aggregation.py
```

Results are persisted into MongoDB.

---

## Spark ML Forecasting

Location:

```text
app/spark_jobs/forecast.py
```

Uses:

```text
Spark MLlib Linear Regression
```

to generate forecasts from historical time-series data.

Run:

```powershell
spark-submit app/spark_jobs/forecast.py
```

Forecasts are persisted into MongoDB.

---

# MCP + LLM Assistant

The platform includes an MCP server that exposes warehouse functionality as tools.

Available tools:

| Tool                    | Description              |
| ----------------------- | ------------------------ |
| get_asset_list          | Retrieve assets          |
| get_latest_price        | Latest asset price       |
| get_asset_price_history | Historical data          |
| compare_assets          | Compare assets           |
| get_asset_stats         | Analytics and statistics |

---

## Start MCP Server

```powershell
uv run findata-mcp
```

---

## Claude Integration

Set:

```env
ANTHROPIC_API_KEY=your_key
```

Then ask:

```text
Show me AAPL trend
Compare AAPL and MSFT
Forecast AAPL
```

The assistant retrieves data from the warehouse before generating responses, ensuring grounded answers and preventing hallucinations.

---

# Testing

The project includes unit tests for:

* DAL operations
* Temporal versioning
* Temporal deletion
* Ingestion normalization
* Provider fallback
* Idempotent ingestion

Run tests:

```powershell
uv run pytest
```

Verbose mode:

```powershell
uv run pytest -v
```

---

# Project Structure

```text
app/
├── analytics/
├── api/
├── db/
├── ingestion/
├── mcp_server/
├── spark_jobs/
└── main.py

streamlit_app/
├── components/
├── services/
├── utils/
└── views/

tests/
├── test_dal.py
└── test_ingestion.py
```

---

# Demonstration Workflow

1. Seed database.
2. Ingest financial data.
3. Start FastAPI.
4. Open Swagger UI.
5. Execute Q1–Q5 endpoints.
6. Run Spark aggregation.
7. Run Spark forecasting.
8. Launch Streamlit dashboard.
9. Demonstrate analytics.
10. Ask questions through the MCP assistant.

---

# Authors

Findata Platform

Financial Data Warehouse Project

FastAPI • MongoDB • Streamlit • Apache Spark • MCP • Claude
