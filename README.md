# Findata Platform

Financial data warehouse (FastAPI + MongoDB) with a Streamlit dashboard and pandas analytics.

## Run the API

```powershell
uv run uvicorn app.main:app --reload
```

Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Analytics endpoint example: `GET http://127.0.0.1:8000/analytics/AAPL`

## Run the Streamlit dashboard

In a second terminal (from the repo root, after `uv sync`):

```powershell
uv sync
uv run streamlit run streamlit_app/app.py
```

Run from the **project root** (`findata-platform`), not from inside `streamlit_app/`.

Optional API URL override:

```powershell
$env:FINDATA_API_URL = "http://127.0.0.1:8000"
uv run streamlit run streamlit_app/app.py
```

Dashboard URL: [http://localhost:8501](http://localhost:8501)

(`streamlit_app/main.py` delegates to `app.py` for backward compatibility.)

## Project layout

| Path | Role |
|------|------|
| `app/main.py` | FastAPI application entry |
| `app/api/routes.py` | Query endpoints Q1–Q5 (`/api/v1/...`) |
| `app/api/analytics_routes.py` | `GET /analytics/{symbol}` (Pydantic v2 response) |
| `app/analytics/analytics_service.py` | pandas/numpy analytics (MA, stats, trend, forecast) |
| `streamlit_app/app.py` | Streamlit entry — sidebar navigation |
| `streamlit_app/views/dashboard.py` | Asset browser, Plotly price/volume chart, OHLCV table |
| `streamlit_app/views/analytics.py` | KPIs, MA chart, statistics & forecast panels |
| `streamlit_app/services/api_client.py` | httpx client (timeouts, retries, errors) |
| `streamlit_app/services/analytics.py` | Client-side MA enrichment for charts |
| `streamlit_app/components/` | Reusable UI: selector, charts, table |
| `streamlit_app/utils/` | Formatting, caching, shared sidebar helpers |

## Dashboard features

- **Sidebar**: asset selector, date range, refresh (clears cache), link to analytics
- **Asset browser**: Symbol, Name, Asset type, Data source (`st.dataframe`, paginated)
- **Price chart**: Plotly close line + volume subplot (zoom, pan, hover, responsive)
- **Time series table**: timestamp/OHLCV, sortable columns, filters, CSV export

## Analytics (Phase 6)

- **Backend**: moving averages (5/20/50), summary stats, daily returns, trend (MA crossover), linear-regression next-close forecast
- **Streamlit Analytics page**: KPI cards, MA chart, statistics panel, forecast explanation — data from `GET /analytics/{symbol}`

Seed or ingest MongoDB data before using the dashboard.

### Ingest price data

```powershell
uv run python -m app.db.seed
uv run python -m app.ingestion.fetch
```

**Nasdaq free tier:** `QUOTEMEDIA/PRICES` sample data only includes a few tickers (e.g. AAPL).  
GOOGL, TSLA, NVDA, etc. return empty from Nasdaq unless you have a paid subscription.

The ingest script **falls back to Yahoo Finance** automatically when Nasdaq returns no rows.

Load only missing symbols via Yahoo:

```powershell
uv run python -m app.ingestion.fetch GOOGL TSLA NVDA --yahoo-only
```

## Phase 7 — MCP + LLM assistant

### Assistant API (for MCP & chat)

| Endpoint | Tool |
|----------|------|
| `GET /assets` | `get_asset_list` |
| `GET /prices/latest/{symbol}` | `get_latest_price` |
| `GET /prices/history?symbol&start_date&end_date` | `get_asset_price_history` |
| `POST /compare` | `compare_assets` |
| `GET /analytics/stats?symbol&window` | `get_asset_stats` |

### Run MCP server (Claude / Cursor)

API must be running first. Then:

```powershell
uv run findata-mcp
```

Or use the bundled Cursor config (`.cursor/mcp.json`) after `uv sync`.

### Streamlit chat

1. Start API + Streamlit (see above).
2. Open **Assistant** in the sidebar.
3. Optional: set `ANTHROPIC_API_KEY` in `.env` for Claude tool-calling.
4. Ask: *Show me AAPL trend last 30 days*

Without an API key, a rule-based router still calls the same tools (grounded, no hallucination).
