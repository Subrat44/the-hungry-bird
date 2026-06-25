# Restro Finder

Restro Finder is a small restaurant-finder web app built to match the architecture diagram:

- FastAPI serves the API and the static frontend.
- Restaurant data is an in-process static catalogue, so there is no database to provision.
- Optional Google Places API Text Search adds live Bengaluru, India restaurant results.
- Nginx reverse proxies public HTTP traffic to uvicorn on `127.0.0.1:8000`.
- systemd keeps the application process running.
- Terraform provisions a GCP VPC, firewall rules, a scoped VM service account, and one e2-micro VM.
- GitHub Actions handles tests, Terraform plan/apply, and SSH-based deploys.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

For live Google Maps results, set `GOOGLE_MAPS_API_KEY` before starting the app.

## Test

```bash
pytest -q
```

## API

- `GET /healthz` returns service health.
- `GET /api/meta` returns available cuisines, areas, tags, and price levels.
- `GET /api/restaurants` lists restaurants with filters:
  - `q`
  - `cuisine`
  - `area`
  - `price`
  - `open_now`
  - `tag`
  - `min_rating`
  - `max_distance_km`
  - `sort=rating|distance|name`
  - `source=local|google`
- `GET /api/restaurants/{restaurant_id}` returns one restaurant.

## Google Maps Bengaluru Search

The Google Maps source uses Google Places API Text Search from the FastAPI server, so the API key is not exposed in browser JavaScript.

```bash
export GOOGLE_MAPS_API_KEY="your-api-key"
uvicorn app.main:app --reload
```

Example:

```bash
curl "http://127.0.0.1:8000/api/restaurants?source=google&q=dosa&area=Indiranagar"
```

The app sends Bengaluru-focused queries such as `dosa in Indiranagar, Bengaluru, Karnataka, India` and normalizes the Places results into the same restaurant card shape used by the UI. If no API key is configured, the Google source returns an empty result with a setup message instead of breaking the page.

## GitHub Secrets

The workflows expect these secrets:

- `GCP_PROJECT_ID`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_TERRAFORM_SERVICE_ACCOUNT`
- `SSH_SOURCE_RANGES`, formatted as a Terraform list string such as `["203.0.113.10/32"]`
- `DEPLOY_SSH_PUBLIC_KEY`
- `DEPLOY_SSH_PRIVATE_KEY`
- `GOOGLE_MAPS_API_KEY`
- `VM_HOST`

## Deployment Flow

1. Terraform creates the network, firewall rules, service account, static IP, and VM.
2. The VM startup script installs Nginx and creates the systemd unit.
3. The deploy workflow copies `app/` and `requirements.txt` to the VM.
4. The deploy workflow builds the virtual environment and restarts `restro-finder`.

## Current Tradeoffs

- No HTTPS yet. Add a domain and Certbot, or put a load balancer in front, before real public use.
- No database. This is intentionally simple and fast, but every data change requires a deploy.
- One VM means simple operations and low cost, but no high availability.
- SSH deploys are straightforward, though a container registry or artifact-based release can be cleaner as the app grows.
