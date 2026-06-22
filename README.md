# Adaptive Anti-Bot AI Crawler

Operations dashboard and API for authorized web crawling, session monitoring, HITL review, and Vietnam gold price collection.

The project combines:

- A FastAPI backend for crawler orchestration, gold price APIs, analytics, login tests, HITL cases, and WebSocket updates.
- A React/Vite operations UI for overview metrics, crawl jobs, safe session metadata, extracted data, gold prices, and human review.
- Multi-source gold crawlers for SJC/WebGia, DOJI, and PNJ, with CSV persistence for historical price analysis.
- Playwright-based browser flows for authorized login checks and blocking signal detection.

## Project Structure

```text
abc/
|-- api_fastapi.py                  # FastAPI backend and API routes
|-- ai_crawler_engine.py            # Multi-source crawler implementations
|-- data_collector.py               # Historical/current gold data collection
|-- data_analyzer.py                # Trend, volatility, momentum, and comparison analytics
|-- fill_all_gaps.py                # Manual historical-data gap filler
|-- login_test_runner.py            # Playwright login-test orchestration
|-- mock_mfa_server.py              # Local mock target for MFA/captcha tests
|-- test_hitl.py                    # Local HITL/blocking scenario smoke test
|-- test_real_login.py              # Interactive login-test runner
|-- config.py.example               # VNAppMob API key template
|-- requirements.txt                # Python dependencies
|-- historical_data/
|   `-- historical_gold_prices.csv  # Local CSV data store
|-- house_price_data/
|   `-- house_price_listings.csv    # Local house-price listing store
|-- sessions/
|   `-- crawler_session_*.json      # Playwright storage-state files
`-- frontend-react/
    |-- package.json                # React/Vite scripts
    |-- src/pages/                  # Dashboard pages
    |-- src/api/                    # API clients
    `-- src/components/             # Shared UI components
```

## Requirements

- Python 3.8+
- Node.js 18+ and npm
- Playwright browsers for browser-based login tests
- Optional: VNAppMob gold API key for historical API backfill
- Optional: local Ollama endpoint for the SJC AI parsing fallback

## Backend Setup

From the `abc` directory:

```powershell
python -m venv ..\venv
..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item config.py.example config.py
```

Edit `config.py` and set:

```python
API_KEY = "your_api_key_here"
```

You can request a VNAppMob key from:

```text
https://vapi.vnappmob.com/api/request_api_key?scope=gold
```

The crawler can still read supported public sources without this key, but historical API backfill depends on it.

## Frontend Setup

From `abc/frontend-react`:

```powershell
npm install
```

The frontend defaults to `http://localhost:8000` for backend calls. To use a different backend URL, create a frontend `.env` file:

```text
VITE_API_BASE_URL=http://localhost:8001
```

## Run Locally

Start the backend from `abc`:

```powershell
..\venv\Scripts\Activate.ps1
uvicorn api_fastapi:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- API root: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

Start the frontend from `abc/frontend-react`:

```powershell
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

## Main UI Areas

- `Overview`: crawler health, source status, latest prices, trends, sessions, jobs, and HITL summary.
- `Crawl Jobs`: source jobs derived from the latest backend payload.
- `Sessions & Identities`: safe metadata for stored Playwright sessions. Cookie values and credentials are not exposed.
- `HITL Review`: starts authorized login tests, shows logs, and surfaces MFA/captcha/access-denied signals.
- `Extracted Data`: topic-oriented extracted-data dashboard routes.
- `Settings`: local app settings surface.

## API Endpoints

Core:

- `GET /api/health`
- `GET /api/current-prices`
- `GET /api/crawl-jobs`
- `GET /api/sessions`
- `WS /ws/prices`

Login tests and HITL:

- `POST /api/login-tests`
- `GET /api/login-tests`
- `GET /api/login-tests/{job_id}`
- `GET /api/login-tests/{job_id}/logs`
- `GET /api/hitl/cases`

Gold data:

- `POST /api/update-historical-data`
- `POST /api/data/update`
- `GET /api/available-dates`
- `GET /api/prices-by-date?date=YYYY-MM-DD`
- `GET /api/historical-prices?company=SJC&days=30`
- `GET /api/export/csv`
- `GET /api/export/house-prices-csv`

Analytics:

- `GET /api/analytics/price-change`
- `GET /api/analytics/volatility`
- `GET /api/analytics/extremes`
- `GET /api/analytics/trends`
- `GET /api/analytics/comparison`
- `GET /api/analytics/source-momentum`

## Crawler Sources

The backend currently supports:

- SJC/WebGia: `https://webgia.com/gia-vang/sjc/`
- DOJI: `https://giavang.doji.vn/`
- PNJ: `https://www.pnj.com.vn/site/gia-vang`

Crawler output is normalized into buy/sell records and used by the dashboard, API responses, CSV persistence, source status tables, and analytics.

## Historical Data

Historical prices are stored in:

```text
historical_data/historical_gold_prices.csv
```

House-price listings are stored in:

```text
house_price_data/house_price_listings.csv
```

Update methods:

```powershell
python fill_all_gaps.py
```

or:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/update-historical-data
```

The backend also checks and updates data during startup/background runs when the collector is available.

## Login Tests and HITL

Login tests are for authorized crawling only. Credentials are accepted by the backend for the current job, redacted from logs, and not displayed in the UI.

Targets supported by `login_test_runner.py`:

- `demo`: `https://practicetestautomation.com/practice-test-login/`
- `github`: `https://github.com/login`
- `custom`: any `http://` or `https://` login URL supplied by the caller

Run the interactive login test:

```powershell
python test_real_login.py
```

Run local MFA/captcha smoke tests:

```powershell
python mock_mfa_server.py
```

In another terminal:

```powershell
python test_hitl.py
```

Detected signals such as MFA, OTP, captcha, Cloudflare, access denied, and timeouts are surfaced as HITL cases for review.

Refresh a real-estate crawler session after Cloudflare/captcha:

```powershell
python refresh_real_estate_session.py batdongsan
python refresh_real_estate_session.py alonhadat
```

Complete the challenge in the browser window, then press Enter in the terminal to save the refreshed session file.

Use Cloak Browser for real-estate sessions by exposing its Chrome DevTools/CDP endpoint, then running:

```powershell
$env:CLOAKBROWSER_CDP_URL="http://127.0.0.1:9222"
python refresh_real_estate_session.py batdongsan
```

Or pass the endpoint directly:

```powershell
python refresh_real_estate_session.py batdongsan --cdp-url "http://127.0.0.1:9222"
```

The crawler will reuse the same `CLOAKBROWSER_CDP_URL` when fetching house-price pages.

House-price crawling runs headless by default. To debug with a visible browser:

```powershell
$env:REAL_ESTATE_HEADLESS="false"
```

## Environment Variables

Optional environment variables used by the crawler:

```text
GOLD_SITE_USER=...
GOLD_SITE_PASS=...
```

These are used as fallback credentials by crawler browser flows. Prefer the HITL/login-test UI for one-off login checks.

## Common Commands

Install backend dependencies:

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

Run backend:

```powershell
uvicorn api_fastapi:app --reload --port 8000
```

Run frontend:

```powershell
cd frontend-react
npm run dev
```

Build frontend:

```powershell
cd frontend-react
npm run build
```

Export CSV:

```powershell
Invoke-WebRequest http://localhost:8000/api/export/csv -OutFile historical_gold_prices.csv
```

## Troubleshooting

Backend cannot start:

- Confirm dependencies are installed in the active virtual environment.
- Confirm port 8000 is free, or run `uvicorn api_fastapi:app --reload --port 8001`.
- Confirm `config.py` exists if using the VNAppMob historical API.

Frontend cannot reach backend:

- Start FastAPI first.
- Confirm the backend URL in `frontend-react/src/api/client.ts` or `VITE_API_BASE_URL`.
- Check browser console/network errors for failed `http://localhost:8000` requests.

Playwright login tests fail:

- Run `python -m playwright install chromium`.
- Confirm the target URL is authorized and reachable.
- Check HITL logs for captcha, MFA, access denied, or timeout signals.

No gold data appears:

- Call `GET /api/current-prices` directly in the browser.
- Run `python fill_all_gaps.py`.
- Check `historical_data/historical_gold_prices.csv`.
- Refresh or replace the VNAppMob API key if historical backfill fails.

## Safety Notes

- Only crawl sites you are authorized to access.
- Do not commit `config.py`, credentials, session files with sensitive cookies, or captured login output.
- The `/api/sessions` endpoint intentionally returns safe metadata only.
- Treat MFA/captcha/access-denied signals as human-review stops, not automatic bypass steps.
