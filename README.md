# ReThread

ReThread helps people find real nearby recycling bins, charity shops, and second-hand stores, then
tracks the value of what they donate, sell, or recycle. Each logged item contributes to a personal
total: cash earned and the estimated water and CO2 avoided compared to buying new.

## Live Deployment

| | |
|---|---|
| **URL** | [https://www.hillaryco.tech/](https://www.hillaryco.tech/) (also reachable at `http://32.192.238.247/`) |
| **Demo username** | `demo_grader` |
| **Demo password** | `RethreadDemo2026!` |

The demo account already has sample entries logged, so the tracker dashboard is populated on first
visit. No signup is required to use the locator.

The application is served through `lb-01`, an HAProxy load balancer distributing traffic across two
identical application servers (`web-01`, `web-02`). TLS is terminated at the load balancer with a
Let's Encrypt certificate that renews automatically.

> Note: the bare apex domain (`hillaryco.tech`, without `www`) does not yet have a DNS record. Only
> `www`, `web-01`, `web-02`, and `lb-01` currently resolve. Adding an `A` record for `@` pointing at
> `32.192.238.247` will bring the apex domain online.

## Features

- **Locator**: searches for real nearby drop-off points (recycling bins, charity shops, second-hand
  stores) using live geocoding and places data, with filters for type, radius, and sort order.
- **Impact tracker**: a personal log of donated, sold, or recycled items, with running totals for
  money earned and water/CO2 avoided, plus per-item detail and filtering.
- **Accounts**: signup and login with hashed passwords and stateless JWT sessions, so either
  application server can handle any authenticated request.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, gunicorn |
| Database | PostgreSQL (managed instance on Supabase) |
| Frontend | Static HTML, CSS, and JavaScript (no build step, no framework) |
| External API | [Geoapify](https://www.geoapify.com/) (Geocoding + Places) |
| Load balancing | HAProxy, round robin with active health checks |
| Deployment | systemd + gunicorn on two application servers, GitHub Actions for CI/CD |

## Project Structure

```
backend/
  app.py            Flask app factory, static frontend serving, /healthz
  wsgi.py           gunicorn entry point
  config.py         Environment-driven configuration
  db.py             psycopg2 connection pool and schema initialization
  errors.py         ApiError and consistent {"error": "..."} JSON error responses
  auth/             Signup/login, password hashing, JWT issue/verify
  locator/          Geoapify geocode and places proxy, with Postgres-backed caching
  tracker/          Diversion log CRUD and impact calculations
frontend/           Static HTML/CSS/JS, calls the API with fetch
deploy/             systemd unit, HAProxy config, and server setup documentation
```

`locator` and `tracker` are independent verticals; they share the same Flask app and Postgres
instance but do not depend on each other directly.

## Local Setup

Requires Python 3.8+ and a PostgreSQL instance (local, Docker, or a free hosted instance such as
Supabase).

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp ../.env.example .env
# Edit .env: set GEOAPIFY_API_KEY and DATABASE_URL

python app.py   # runs on http://localhost:8000, creates tables on first boot
```

Open `http://localhost:8000`. The frontend is served by the same Flask app, so there is nothing
separate to build.

### Environment Variables

| Variable | Purpose |
|---|---|
| `GEOAPIFY_API_KEY` | Server-side only. The frontend calls this application's own `/api/locator/*` endpoints, which proxy Geoapify; the key is never sent to the browser. |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname`, shared by both application servers. |
| `SESSION_SECRET` | HMAC secret used to sign JWTs. |
| `JWT_EXP_HOURS` | Token lifetime (default 168 hours / 7 days). |
| `GEOAPIFY_CACHE_TTL_SECONDS` | How long a cached places result is served before re-querying Geoapify (default 1 hour). |

## Error Handling

| Case | Behavior |
|---|---|
| Ambiguous or unknown city | `/api/locator/geocode` returns a list of candidate matches; `404` if nothing matches at all |
| Geoapify unavailable or rate-limited | Serves the last cached result for that query, flagged `stale: true`; `502` only if no cache exists |
| No drop-off points in radius | `200` with an empty `results` array and a plain-language `message` suggesting a wider radius |
| Unrecognized log category | Falls back to a generic average weight factor; the entry is still accepted |
| Invalid `amount_earned` or `weight_kg` | `400` with `{"error": "..."}`; the entry is rejected and totals are left unchanged |
| Auth failure | `401` with `{"error": "..."}` on tracker endpoints (the locator remains fully public) |

## Deployment Architecture

Two identical application servers sit behind a load balancer. Both are stateless and read/write the
same Postgres instance; there is no server-side session store or per-instance database, so either
application server can answer any request.

| Role | Public IP | Private IP | Runs |
|---|---|---|---|
| **web-01** | `52.207.253.107` | `10.227.50.192` | gunicorn, port 8000 |
| **web-02** | `100.53.143.147` | `10.227.102.34` | gunicorn, port 8000 |
| **lb-01**  | `32.192.238.247` | `10.227.41.131` | HAProxy, ports 80/443 (public), stats on 8404 |

**Database**: managed PostgreSQL on [Supabase](https://supabase.com/), reached over TLS
(`sslmode=require`) via its session pooler. Both application servers use the same `DATABASE_URL`.
The database is not self-hosted on either application server, so there is no local Postgres port to
firewall.

Full step-by-step server provisioning, including firewall configuration, is documented in
[`deploy/SERVER_SETUP.md`](deploy/SERVER_SETUP.md).

### Load Balancer

`deploy/haproxy.cfg` configures round-robin balancing across web-01 and web-02 with an active
health check (`option httpchk GET /healthz`, checked every 5 seconds). HAProxy performs active
health checks natively, which is why it was chosen over a passive-check-only reverse proxy.

**Firewall**: web-01 restricts port 8000 to lb-01's private IP only
(`sudo ufw allow from 10.227.41.131 to any port 8000 proto tcp`), so the application port is not
reachable from the public internet, only from the load balancer. web-02 does not yet have this
restriction applied; the same rule should be added there to match web-01.

### Verifying Load Distribution

Confirmed by comparing HAProxy's session counters before and after a burst of requests:

```bash
for i in $(seq 1 20); do curl -s -o /dev/null http://32.192.238.247/healthz; done
curl -s "http://32.192.238.247:8404/stats;csv" | grep rethread_back
```

A 20-request burst split evenly, 10 requests to each server, with both backends reporting
`status=UP` and `check_status=L7OK`. The HAProxy stats page is browsable at
`http://32.192.238.247:8404/stats`.

## Continuous Deployment

`.github/workflows/deploy.yml` redeploys automatically on every push to `main`, and can also be run
manually from the Actions tab. On each run it:

1. Syncs `backend/`, `frontend/`, and `deploy/` to both web-01 and web-02, excluding local secrets
   and installed packages.
2. Installs dependencies and restarts the `rethread` service on each server, checking `/healthz`
   before continuing.
3. Pushes the HAProxy configuration to lb-01, validates it, and reloads HAProxy.
4. Runs a final health check through the public load balancer URL.

Deployment authenticates with a dedicated SSH key scoped only to this purpose, separate from any
personal key. To enable the workflow in this repository, add the private key as a repository secret
named `DEPLOY_SSH_KEY` under **Settings → Secrets and variables → Actions**.

## Design Decisions

- **Locator category mapping**: Geoapify's Places API groups charity shops and other second-hand
  stores under a single category. Results are split into "charity shop" versus "second-hand store"
  by matching place names against common charity chain keywords (Oxfam, Goodwill, Salvation Army,
  "thrift", etc.); anything unmatched is labeled "second-hand store."
- **No "pays for drop-off" filter**: Geoapify's data does not reliably indicate which locations pay
  for clothing, so the locator does not attempt to filter on this. Payout information is instead
  self-reported by users in their own log entries.
- **City disambiguation**: `/api/locator/geocode` always returns a list of candidates, and the
  frontend always shows a picker rather than silently selecting the top result, so an ambiguous city
  name never resolves to the wrong place.
- **Geoapify outage or rate limit**: every geocode and places lookup is cached in Postgres, keyed by
  rounded coordinates and radius, or by query text for geocoding. A live call failure falls back to
  the cached result regardless of age, flagged `stale: true`. A `502` is only returned if no cache
  exists at all.
- **Unrecognized log category**: category is free text; unrecognized values fall back to a generic
  average weight rather than rejecting the entry.
- **Currency**: totals are shown with a `£` prefix, matching the UK-based source used for the
  impact-factor calculations.

## Impact Methodology

The water and CO2 figures shown in the tracker are avoided-impact estimates, not direct
measurements of a specific garment. They represent the difference between a new replacement garment
being manufactured and the original garment being reused or recycled instead. Life-cycle studies
vary in their per-kilogram figures depending on fiber type and methodology, which is why this
project cites one specific source rather than presenting a number as universal fact.

**Source**: WRAP (Waste & Resources Action Programme, UK), *Textiles 2030 Annual Progress Update
2022-23* (published 2023).
[Read the report](https://www.wrap.ngo/resources/report/textiles-2030-annual-progress-update-2022-23)

- **CO2**: WRAP reports an average net saving of 4.0 tonnes CO2e per tonne of textiles reused, and
  0.7 tonnes CO2e per tonne recycled, relative to manufacturing an equivalent new garment. Used
  directly as 4.0 / 0.7 kg CO2e avoided per kg.
- **Water**: WRAP reports that 233,500 tonnes of textiles handled through reuse and recycling in
  2022 avoided roughly 385 million cubic metres of water. This project derives a blended rate from
  that figure (385,000,000 m³ ÷ 233,500 t ≈ 1,649 litres avoided per kg), applied to both resold and
  recycled entries, since WRAP does not publish a per-method split for water.
- **"Days of drinking water" framing**: uses the European Food Safety Authority's guidance of
  approximately 2.0 litres per day as the divisor.
- Figures are rounded to one decimal place; the intent is directional education, not precise
  measurement.

## Demo Video

[Add demo video link here]

## Credits

- Place data: [Geoapify](https://www.geoapify.com/) (Places API and Geocoding API, free tier).
- Impact figures: [WRAP UK, *Textiles 2030 Annual Progress Update 2022-23*](https://www.wrap.ngo/resources/report/textiles-2030-annual-progress-update-2022-23) (2023).
- Map tiles: [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, via [Leaflet](https://leafletjs.com/).
