# Restro Finder

Restro Finder is a small FastAPI restaurant-finder for Bengaluru. It ships with
a static catalogue of 10 curated restaurants for instant, reliable results,
and an optional live source backed by the free OpenStreetMap Overpass API for
real-time data — no paid API key required for either.

## Goal

- Search and filter Bengaluru restaurants by cuisine, area, price, rating, and tags
- Work instantly with zero setup, using a built-in demo dataset
- Optionally pull live restaurant data from OpenStreetMap
- Degrade gracefully (never crash the page) if the live source is unavailable
- Run as a single small FastAPI service, deployable for free on Render

---

# High Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                            Browser                           │
│                                                              │
│  index.html + script.js                                      │
│  - Renders filters, restaurant cards, and the detail panel   │
│  - Calls the API on page load and on every filter change     │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ GET /api/meta
                              │ GET /api/restaurants?...
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI App  (app/main.py)                  │
│            hosted on Render, auto-deployed from `main`       │
│                                                              │
│ Responsibility:                                              │
│ - Serve the static frontend                                  │
│ - Expose /healthz, /api/meta, /api/restaurants               │
│ - Apply filters: q, cuisine, area, price, rating, tag, sort  │
└──────────────────────────────────────────────────────────────┘
                              │
            source=local      │      source=google
        ┌─────────────────────┴─────────────────────┐
        ▼                                            ▼
┌─────────────────────────────┐          ┌─────────────────────────────────┐
│    Static Catalogue         │          │    Live OpenStreetMap Search    │
│    (app/data.py)            │          │    (app/google_places.py)       │
│                             │          │                                 │
│ - 10 curated Bengaluru      │          │ - Queries the Overpass API for  │
│   restaurants, baked into   │          │   restaurants in a Bengaluru    │
│   the app                   │          │   bounding box                  │
│ - Always available, no      │          │ - Retries a second mirror, the  │
│   network dependency        │          │   degrades to an empty list wit │
│                             │              a friendly message            │
└─────────────────────────────┘          └─────────────────────────────────┘
        │                                           │
        └─────────────────────┬─────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│         JSON: { "count", "restaurants", "message" }          │
│         sent back to the browser and rendered as cards       │
└──────────────────────────────────────────────────────────────┘
```

# End-to-End Workflow

```text
User opens the page
        │
        ▼
Browser loads /api/meta
        │
        └── Builds cuisine / area / tag dropdowns
        │
        ▼
Browser loads /api/restaurants (source=local by default)
        │
        ▼
User changes a filter or types a search term
        │
        ▼
script.js rebuilds the query string
        │
        ▼
GET /api/restaurants?q=...&cuisine=...&source=local|google
        │
        ▼
FastAPI: list_restaurants()
        │
        ├── source = local
        │      │
        │      ▼
        │    Filter / sort the static catalogue (app/data.py)
        │
        └── source = google
               │
               ▼
             search_bengaluru_restaurants() (app/google_places.py)
               │
               ├── Query Overpass API (Bengaluru bounding box)
               ├── Retry on a second mirror if the first fails
               └── Normalize OSM tags into restaurant cards
        │
        ▼
Response: { "count": N, "restaurants": [...], "message": ... }
        │
        ▼
script.js renders the result cards
        │
        ├── 0 results  → shows "message" (e.g. rate-limited)
        └── 1+ results → auto-selects the first card
        │
        ▼
User clicks a card
        │
        ▼
Detail panel updates with name, cuisine, hours, address, tags
```

---

## Project Structure

```text
the-hungry-bird/
├── .github/
│   └── workflows/
│       ├── ci.yml            # Runs pytest on every push/PR
│       ├── deploy.yml        # SSH deploy to a GCP VM (optional, not the live site)
│       └── terraform.yml     # Terraform plan/apply for the GCP VM (optional)
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app: routes, filtering, sorting
│   ├── data.py                # Static catalogue of 10 demo restaurants
│   ├── google_places.py       # Live OpenStreetMap (Overpass) search
│   ├── static/
│   │   ├── script.js          # Frontend logic: filters, rendering, detail panel
│   │   ├── style.css
│   │   └── bengaluru-restaurant.svg
│   └── templates/
│       └── index.html         # Single-page UI
├── tests/
│   └── test_app.py            # pytest suite
├── nginx/
│   └── restro-finder.conf     # Reverse proxy config (GCP VM path only)
├── systemd/
│   └── restro-finder.service  # systemd unit (GCP VM path only)
├── terraform/
│   ├── main.tf                # GCP VPC, firewall, VM (optional infra path)
│   ├── variables.tf
│   ├── outputs.tf
│   └── startup-script.sh
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8001`.

No API key is required — the demo source works immediately, and the live
OpenStreetMap source works with zero configuration too.

## Test

```bash
pytest -q
```

## API

- `GET /healthz` — service health
- `GET /api/meta` — available cuisines, areas, tags, and price levels
- `GET /api/restaurants` — list restaurants with filters:
  - `q`, `cuisine`, `area`, `price`, `open_now`, `tag`, `min_rating`, `max_distance_km`
  - `sort=rating|distance|name`
  - `source=local|google` (`google` = live OpenStreetMap data, see below)
- `GET /api/restaurants/{restaurant_id}` — one restaurant

## Live Data Source (OpenStreetMap)

The `source=google` option is labeled "Google Maps" in the UI for historical
reasons, but it's actually backed by the **free OpenStreetMap Overpass API** —
no API key, no billing. `app/google_places.py`:

- Queries restaurants inside a Bengaluru bounding box
- Tries a second public mirror if the first one fails or rate-limits
- Returns `{"count": 0, "restaurants": [], "message": "..."}` instead of
  crashing if both mirrors fail — the public Overpass API is known to
  rate-limit requests from cloud/CI IP ranges (this bit both our GitHub
  Actions runs and Render itself during testing)

```bash
curl "http://127.0.0.1:8001/api/restaurants?source=google&q=dosa"
```

## Deployment

**Live site:** [the-hungry-bird.onrender.com](https://the-hungry-bird.onrender.com),
hosted on Render, auto-deployed on every push to `main`.

The repo also contains an optional infrastructure-as-code path
(`terraform/`, `nginx/`, `systemd/`, `.github/workflows/deploy.yml`) for
running this app on a self-managed GCP VM instead. This path is **not**
currently active — it needs `terraform apply` run once and the secrets below
configured before its GitHub Action will succeed.

### GitHub Secrets (only needed for the GCP VM path)

- `GCP_PROJECT_ID`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_TERRAFORM_SERVICE_ACCOUNT`
- `SSH_SOURCE_RANGES`, e.g. `["203.0.113.10/32"]`
- `DEPLOY_SSH_PUBLIC_KEY`
- `DEPLOY_SSH_PRIVATE_KEY`
- `GOOGLE_MAPS_API_KEY` (unused by the app today, kept for the VM path)
- `VM_HOST`

## Known Limitations

- The Overpass API is a shared free service and can be empty/rate-limited at
  times — there's no paid fallback, by design, to keep this project at $0 cost.
- No database — every data change to the demo catalogue requires a deploy.
- No HTTPS on the optional GCP VM path; Render provides this automatically.
- One VM (if using the GCP path) means low cost but no high availability.