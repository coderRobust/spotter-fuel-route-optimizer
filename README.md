# FuelRoute Optimizer — Spotter AI Backend Django Engineer Assessment

Django REST Framework implementation that produces an OSRM driving route and estimates a cost-effective fuel-purchase plan given 500-mile vehicle range and 10 MPG.

**Important scope honesty**: This repository contains the original supplied CSV, but that dataset has *no station coordinates*. This assessment implementation uses a limited bundled **city-centroid seed** to illustrate the end-to-end solution. A city center is NOT a real truckstop location or confirmed highway exit. Consequently, the cost optimization is optimal only for the simplified fixed-route, zero-detour model and MUST NOT be described as real-world globally optimal until address-level station geocoding and road-access detour modeling are added. Some trips can legitimately return 422. The project is a functional, explicitly limited assessment starter, not a verified complete road-trip navigation product.

## Quick start in VS Code (Windows)
Read [docs/VSCODE_WINDOWS_STEP_BY_STEP.md](docs/VSCODE_WINDOWS_STEP_BY_STEP.md). Basic commands:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate --noinput
python manage.py import_stations
python manage.py runserver
```
Swagger at http://127.0.0.1:8000/api/docs/; import `postman_collection.json` into Postman.

Docker/ PostgreSQL optional: `docker compose build`; `docker compose up -d db`; `docker compose run --rm api python manage.py migrate --noinput`; `docker compose run --rm api python manage.py import_stations`; `docker compose up -d api`.

## Request
```json
{
  "start": "Chicago, IL",
  "finish": "Los Angeles, CA",
  "vehicle": {"max_range_miles": 500, "mpg": 10, "starting_fuel_gallons": 50},
  "corridor_miles": 15
}
```
Optional: use `start_coordinates` and `finish_coordinates` containing `{ "lat": 41.8781, "lon": -87.6298 }` to bypass geocoding. Supports contiguous US coordinate ranges only; a coordinate inside the bounding box isn't proof of US jurisdiction.

Response: `route` with miles, minutes, GeoJSON LineString; `fuel_plan` with stops, gallons purchased, cost and remaining fuel; `metadata` with approximation disclaimers and cache indicator.

## Optimization
- Fuel capacity = range / MPG (default 50 gallons).
- Starting fuel defaults to full tank, and its historical purchase price is excluded from **additional fuel purchased** cost.
- Station list is projected to a route chain. Cheapest duplicate station at same mile marker retained.
- At each station, if a strictly cheaper station or destination is reachable, buy just enough to reach it; otherwise buy up to tank capacity or quantity needed to reach destination.
- Formula: purchase cost = sum(gallons purchased at station × supplied USD price per gallon).
- The algorithm is optimal under a continuous-fuel, no-detour, known-prices, fixed-route assumption. No turn-by-turn detour verification is performed.
- Station positions are projected onto route segments. OSRM segment distance annotations are used when available; otherwise station mile markers use globally scaled geometry as an explicitly disclosed approximation.
- Current model treats fuel station access as on-route even when station is only near the road. This can lead to unrealistic routes; **not yet suitable for navigation decisions**.

## Data policy
The source CSV has repeated `OPIS Truckstop ID` entries and occasional conflicting prices; lacking timestamps, loader retains the **lowest recorded price** for each OPIS ID+city+state combination. This is a *deliberate optimistic data assumption*, not evidence that that price is currently offered. Import is idempotent. Only cities provided in `data/city_centroids.json` receive coordinates, all other station rows remain in DB with NULL geolocation.

**Path to a higher-quality submission**: Pre-geocode every distinct station location offline using a licensed/bulk geocoding provider or trusted station coordinates. Store confidence level and exact coordinates. Verify road access via snapping and limited routing calls for shortlisted stops; account for detour costs. Keep API routing calls within the employer's 1–3 target. Add spatial index or PostGIS when station count/throughput warrants it. GeoNames city-center lookups are not enough for location-precise optimization. Do not hammer public Nominatim for bulk geocoding.

## External service calls
A request can use 0–3 external calls: one OSRM route request, plus up to two Nominatim requests when both endpoints are absent from presets/cache. Route caching applies per process via local-memory cache. This **does not persist across Gunicorn workers**; Redis recommended for deployment. Third-party public services have rate limits/no guaranteed availability.

## Quality commands
```bash
python manage.py check
python -m pytest -q
```
The project uses SQLite by default for a quick start and PostgreSQL in Docker. Geospatial filtering is presently in Python, not PostGIS. No deployment target or production throughput guarantee is claimed.

## Evaluation limitations / future work
- Exact truckstop coordinates and station access roads; bulk geocoding is not completed.
- Realistic detours, route rerouting, and road restrictions are not represented.
- Cost is not the cost of an initially filled tank; if total **consumed** fuel valuation is wanted, a starting-fuel price model is required.
- OSRM demo server is not a service-level-agreement-backed production routing API.
- Price changes and contradictory records need provenance / timestamp information.
- Benchmark latency and throughput on your own machine and publish measured results, rather than unsupported numbers.

## Deliverables
- Source, supplied data, import command, tests, Swagger docs, Postman collection, Docker files and CI workflow.
- Loom script in `docs/LOOM_SCRIPT.md`. **A Loom recording is not included**; record a genuine running demo before submitting.

## Station coordinate review and current validation

See [the reproducible station review workflow](docs/STATION_VERIFICATION.md) and [the implementation validation report](docs/ASSESSMENT_VALIDATION.md). Offline POI matching never auto-verifies a station. Verified imports now require independent review evidence, attribution and duplicate-assignment checks. Existing city centroids remain available as approximate candidates; the API does not certify them as actual forecourt locations. Historical verified labels without evidence are not independently validated.
