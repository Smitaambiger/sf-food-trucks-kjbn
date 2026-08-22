# SF Food Trucks Nearby

A small backend service (with a minimal map front-end) that answers one question:
**"What food trucks are operating near me right now?"**

Built for the KJBN Labs Python Backend Developer coding challenge — **Back-end track**,
project: **Food Trucks**.

Live demo: `<ADD_YOUR_DEPLOYED_URL_HERE>`
Interactive API docs (Swagger): `<ADD_YOUR_DEPLOYED_URL_HERE>/docs`

---

## What it does

- Takes a `lat`/`lon` and an optional radius + food-type filter.
- Pulls San Francisco's official [Mobile Food Facility Permit dataset](https://data.sfgov.org/Economy-and-Community/Mobile-Food-Facility-Permit/rqzj-sfat)
  from DataSF (Socrata Open Data API), keeping only active permits (`APPROVED`, `ISSUED`, `REQUESTED`).
- Computes real distance (haversine formula) from the query point to every truck, filters by radius,
  optionally filters by a food-type keyword, and returns the closest matches sorted by distance.
- A single-page front-end (Leaflet map) lets you click anywhere on the map — or use your browser's
  geolocation — to see nearby trucks as pins, with a matching list/sidebar.

## Why this project / track

The role is Python Backend Developer, so I picked the **Back-end track**: the API is written,
tested and documented as if another team were going to consume it, and the front-end is
intentionally minimal (a single static page + FastAPI's auto-generated Swagger docs at `/docs`)
rather than a polished SPA.

---

## Architecture

```
app/
  main.py              # FastAPI app wiring: middleware, routers, exception handlers, static mount
  core/
    config.py           # Settings loaded from environment variables (pydantic-settings)
    logging.py           # Structured logging + per-request request_id
    exceptions.py         # Domain exceptions -> HTTP status mapping
  api/
    deps.py               # Dependency-injected singletons (TruckService)
    routes/
      trucks.py            # GET /api/v1/trucks/nearby
      health.py             # GET /health
  schemas/
    truck.py                # Pydantic request/response models
  services/
    datasf_client.py         # All outgoing HTTP calls to DataSF live here (timeouts, retries, errors)
    truck_service.py          # Business logic: caching, filtering, distance sort
  utils/
    geo.py                    # Haversine distance + lat/lon validation (pure functions, easy to unit test)
  static/                     # Minimal front-end: index.html + app.js (Leaflet) + styles.css
tests/                        # pytest suite mirroring the app layers
```

**Layering rationale:** routes only translate HTTP <-> Python calls; all business logic lives in
`services/`; all "talking to the outside world" lives in `datasf_client.py`. This means the service
layer is unit-tested with a mocked client (no network calls in most tests), and the client itself is
tested separately against a mocked HTTP layer (`respx`) to cover retry/timeout/error behavior.

### Design decisions worth calling out

- **In-memory cache with TTL** (`truck_service.py`): the truck dataset changes slowly (new permits
  are issued occasionally, not every second), so re-fetching all ~300+ rows from DataSF on every
  request would be wasteful and slow. The service caches the parsed dataset for `CACHE_TTL_SECONDS`
  (default 15 min) behind an `asyncio.Lock` so concurrent requests don't stampede the upstream API.
- **Retries with backoff-free short-circuiting** (`datasf_client.py`): transient errors (timeouts,
  connection resets, 5xx) are retried up to `DATASF_MAX_RETRIES` times; 4xx errors fail fast since
  retrying a bad request won't help.
- **Malformed rows are dropped, not fatal**: a handful of DataSF rows have missing or `0,0`
  coordinates. Rather than letting the whole request fail, `_parse_truck` filters these out and logs
  how many rows were usable.
- **Validation at the boundary**: FastAPI's `Query(..., ge=-90, le=90)` catches obviously malformed
  input (HTTP 422) before it reaches the service layer; the service layer re-validates because it's
  a public method other code paths could call directly, and enforces business rules like max radius.

---

## API

### `GET /api/v1/trucks/nearby`

| Param       | Type   | Required | Notes                                      |
|-------------|--------|----------|---------------------------------------------|
| `lat`       | float  | yes      | -90..90                                     |
| `lon`       | float  | yes      | -180..180                                   |
| `radius_km` | float  | no       | default `1.0`, max `10.0`                   |
| `food_type` | string | no       | case-insensitive substring match on menu    |
| `limit`     | int    | no       | default/max `50`                            |

Example:

```bash
curl "http://localhost:8000/api/v1/trucks/nearby?lat=37.7749&lon=-122.4194&radius_km=2&food_type=tacos"
```

```json
{
  "query_lat": 37.7749,
  "query_lon": -122.4194,
  "radius_km": 2.0,
  "count": 2,
  "results": [
    {
      "permit": "25MFF-00042",
      "applicant": "Bay Area Mobile Catering, Inc. dba. Taqueria Angelica's",
      "food_items": "Tacos: burritos: soda & juice",
      "address": "1455 MARKET ST",
      "status": "APPROVED",
      "latitude": 37.775228,
      "longitude": -122.417466,
      "distance_km": 0.174
    }
  ]
}
```

### `GET /health`

Basic liveness check, returns `{"status": "ok"}`.

Full interactive documentation (auto-generated by FastAPI) is available at `/docs` once the
server is running.

---

## Running it locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash / macOS / Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env               # defaults work out of the box, no API key required

uvicorn app.main:app --reload
```

Then open `http://localhost:8000` for the map UI, or `http://localhost:8000/docs` for the API docs.

### Configuration

All configuration is via environment variables (see `.env.example`) — nothing is hardcoded.
Notably `DATASF_APP_TOKEN` is optional: the dataset is public and works without one at low volume,
but a free token (from [data.sfgov.org](https://data.sfgov.org/profile/app_tokens)) avoids
throttling under heavier use.

## Tests

```bash
pytest -v          # 18 tests: geo math, service logic, HTTP client retry/error behavior, API layer
ruff check .        # lint
```

Tests are split by layer:
- `test_geo.py` — pure distance/validation math, no mocking needed.
- `test_truck_service.py` — business logic (caching, filtering, sorting) with the DataSF client mocked.
- `test_datasf_client.py` — HTTP retry/timeout/error handling, using `respx` to mock the network layer.
- `test_api_trucks.py` — FastAPI routes, using `TestClient` with the service layer mocked via
  dependency override.

## Logging & error handling

Every request gets a short `request_id` (propagated via the `x-request-id` header if the caller
supplies one), included in every log line for that request so a single request's logs can be
traced end-to-end. Domain errors (`AppError` subclasses) are mapped to proper HTTP status codes by
a central exception handler instead of leaking stack traces; unexpected exceptions still surface as
500s in the logs for debugging.

## Docker

```bash
docker build -t sf-food-trucks .
docker run -p 8000:8000 --env-file .env sf-food-trucks
```

## Deployment

Deployed on `<Render / Railway / Fly.io - fill in>`: `<ADD_YOUR_DEPLOYED_URL_HERE>`

`render.yaml` in the repo root defines a ready-to-use [Render](https://render.com) blueprint:

1. Push this repo to GitHub.
2. On Render: New -> Blueprint -> connect the repo (Render will pick up `render.yaml` automatically
   and build the included `Dockerfile`).
3. Add environment variables from `.env.example` if you want to override any defaults (all are
   optional; you may want to set `DATASF_APP_TOKEN`).
4. Render will use `healthCheckPath: /health` to confirm the service is up.

(Without the blueprint: New -> Web Service -> connect the repo -> build command
`pip install -r requirements.txt` -> start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.)

## Manual API testing

`postman_collection.json` has ready-made requests for `/health`, a nearby search, a food-type-filtered
search, and an invalid-input case (expects `422`). Import it into Postman/Insomnia and set the
`base_url` variable to your local or deployed URL.

## Possible next steps (out of scope for this challenge)

- Persist the truck dataset in a real cache (Redis) instead of in-process memory, for multi-instance
  deployments.
- Add a background scheduler to refresh the cache proactively instead of on-demand.
- Geocode free-text addresses to lat/lon for users without geolocation.

---

## Developer

**Name:** Smita D Ambiger
**Experience:** 2.5 years as a Backend Engineer (Accenture) building REST APIs and backend systems
with Python, FastAPI, and Django REST Framework — including Pydantic-based validation, structured
logging, PostgreSQL query optimization, and CI/CD pipelines on GCP. Also an active open-source
contributor to Apache Burr (Apache Software Foundation), with merged PRs adding FastAPI integration
utilities and AST-based static validation.
**Contact:** smitaambiger11@gmail.com | +91 96110 13135

*Note on tooling: AI-assisted tooling (Claude) was used as a pair-programming aid while building this —
for scaffolding, boilerplate, and reviewing logic — the same way I use Claude/Cursor in my day-to-day
work. All architectural decisions, the dataset/track choice, and the final code are mine, reviewed and
tested before submission, and I can walk through any part of it in the demo.*
