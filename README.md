# FuelRoute Optimizer — Django backend assessment

Django REST Framework API for US driving routes and cost-effective fuel purchases using the supplied assessment CSV. Defaults: **500-mile tank range, 10 MPG, 50 gallons starting fuel**. Returns route GeoJSON, a rendered map link, station identities, purchase quantities, fuel balances and total additional purchase cost.

A real Chicago → Los Angeles request has been demonstrated with **seven road-access-verified purchases across 2,025.81 miles for $532.88**. The station preparation is reproducible offline. See [actual request/results and validation](docs/ASSESSMENT_VALIDATION.md).

**Model boundary:** purchases minimize cost among the available verified candidates on the chosen fixed route; the default also road-routes through selected stations and includes detour fuel. This is not a global road-network optimum. The bundle contains 12 manually source-reviewed locations and 94 exact cross-source station matches; nationwide station-level coverage remains incomplete. Trips without sufficient verified coverage return 422. City centroids are excluded by default.

## Run locally

Python 3.13 recommended. Django **6.1.2** is pinned, verified against the [official current stable release](https://www.djangoproject.com/download/) on 25 October 2026.

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Copy .env.example to .env and set your local configuration/contact.
python manage.py migrate --noinput
python manage.py import_stations
python manage.py prepare_corridor_coordinates --apply
python manage.py prepare_nationwide_coordinates --apply
python manage.py runserver
```

For an older existing database created with syncdb, back it up and use `python manage.py migrate --fake-initial --noinput` once. See [station verification and migration details](docs/STATION_VERIFICATION.md).

- Health: http://127.0.0.1:8000/health/
- Swagger: http://127.0.0.1:8000/api/docs/
- Station coverage: http://127.0.0.1:8000/api/v1/stations/stats/
- Postman: import `postman_collection.json`; run requests in order, then open the returned `map_url` in a browser.

## Request and map

`POST /api/v1/routes/optimize/`

```json
{
  "start": "Chicago, IL",
  "finish": "Los Angeles, CA",
  "vehicle": {
    "max_range_miles": 500,
    "mpg": 10,
    "starting_fuel_gallons": 50
  }
}
```

`start_coordinates` and `finish_coordinates` objects with `lat` and `lon` can replace text endpoints. Bounds include Alaska and Hawaii, but a bounding box does not prove US jurisdiction. A disconnected driving route returns 422; no ocean connection or missing station location is invented. Nominatim queries are restricted to the US.

Success includes `route`, `fuel_plan`, `metadata` and `map_url`, e.g. `/maps/<token>/`. Open that path on the same API host. The map displays the computed road route and actual selected stations, using MapLibre GL JS and attributed OpenFreeMap vector tiles; it makes **no new routing request**. Browser tile/CDN requests are separate from the routing/geocoding call budget. The map expires with the cache; repeat the POST if it expires.

Errors: **400** invalid input/location, **422** no driving route or insufficient station coverage, **502** upstream timeout/unavailable/malformed provider response. Fuel infeasibility includes gap diagnostics. An explicit `allow_approximate_stations: true` enables legacy approximate coordinates for exploration, clearly labeled; keep it false for the assessment demonstration.

## Fuel model and accuracy

Capacity is range / MPG. Starting fuel defaults to a full 50-gallon tank and is **excluded from additional purchase cost**. To model paying for all fuel during this trip, use zero starting fuel only when a verified station is available at the origin. The response separately reports purchased, consumed and arrival fuel; no historical starting-fuel price is fabricated.

At each station, buy enough to reach the first strictly cheaper reachable station (or destination); otherwise fill to capacity or the remaining trip requirement. Equal-position candidates retain the lowest price. This greedy rule minimizes additional purchase cost in the stated fixed-route model; tests compare it with an independent exhaustive dynamic-programming oracle. By default, a second routing request routes through selected stations, checks fuel-stop road snaps within 75 meters (place-name endpoints retain OSRM default snapping), and recalculates fuel using actual routed legs. This validates access for the selected plan, but does not search every possible combination of alternate stations. Set `verify_road_access` to `false` only to use projected stops and a single routing request. Calculations use Decimal internally and round only at presentation; sums of individually rounded stop costs can differ slightly from the total.

Stations project onto the closest route segment to generate the initial candidate plan. Per-segment OSRM distance annotations avoid global geometry scaling when available; fallback scaling is disclosed in metadata. The default access-check route includes ramps/service-road detours in fuel consumption. Route loops can make nearest-segment projection ambiguous, and the final result is not a global road-network optimum.

## Source data and station preparation

The supplied CSV contains 8,151 observations and 6,738 OPIS/city/state identities. Import rejects invalid prices and reports duplicates/conflicts. Without timestamps, the existing rule keeps the **minimum recorded price** per identity: an optimistic historical-price assumption, not a current quote. The original CSV preserves provenance.

The bundled [reviewed OSM subset](data/verified_corridor/README.md) provides **12 station-specific locations**. Store/OPIS/city/state/exit identities were independently checked against official operator listings. Coordinates come from actual fuel nodes or reviewed canopy footprints, not city centers. The [nationwide match data](data/nationwide/README.md) adds **94 exact operator/store/CSV/OSM identity matches**; these are cross-source checked, not claimed as field visits. Attribution and matching evidence are included. The two preparation commands regenerate their ignored CSVs and invoke the same transactional coordinate importer.

[Generic offline matching](docs/STATION_VERIFICATION.md) creates review candidates only; it never automatically verifies a result. Verified imports require attribution, provider identity, reviewer, review timestamp and evidence; duplicate assignments and conflicting verified coordinates are rejected. A clone can reproduce the reviewed subset without geocoding keys or live station queries.

## Performance and verification

Each optimization uses one OSRM request for the base route and, by default, one more to route through selected stations. Both are cached; projected-only mode uses the base route alone. Uncached text endpoints may add up to two geocoding calls; preset/cached endpoints avoid geocoding. An indexed bounding box filters stations before projection; candidates are never truncated by an early route-position limit. File-based cache shares routes/maps across local Gunicorn workers. Configure `CACHE_LOCATION` on a private writable shared filesystem for local workers; a multi-host deployment needs an appropriate shared cache backend.

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q
python scripts/verify_demo.py --require-success
```

The last command uses real external routing, measures cold/warm latency and call counts, and independently audits returned station identity, prices, order, tank capacity, fuel balance and cost. Test cases mock external providers. See [validation](docs/ASSESSMENT_VALIDATION.md) for actual measurements rather than throughput promises.

Public OSRM/Nominatim/OSM tiles have usage limits and no uptime guarantee. No bulk Nominatim geocoding occurs during setup or optimization. Provider keys, databases, caches and unreviewed provider exports are ignored by Git.

## Docker and submission

```sh
docker compose build
docker compose up -d db
docker compose run --rm api python manage.py migrate --noinput
docker compose run --rm api python manage.py import_stations
docker compose run --rm api python manage.py prepare_corridor_coordinates --apply
docker compose run --rm api python manage.py prepare_nationwide_coordinates --apply
docker compose up -d api
```

The Docker settings are for local demonstration; use real secrets, DEBUG=0, HTTPS, trusted hosts and managed services before production. Docker execution is not included in the local validation claim.

GitHub Actions checks migrations, clean station preparation and tests. The employer also requires a **real Loom recording, at most five minutes**, demonstrating Postman and a code overview, plus submission within three days. Recording/uploading Loom and the employer's questionnaire remain outside this technical work. Do not claim a video or timely submission exists until actually completed.

### Basemap and station-access diagnostics

The default basemap is the OpenFreeMap Liberty vector style, rendered with MapLibre GL JS. Set `BASEMAP_STYLE_URL` to another permitted MapLibre style if required. Map responses use `Referrer-Policy: strict-origin-when-cross-origin`: providers receive the real application origin, without the map-token path. Attribution to OpenFreeMap, OpenMapTiles and OpenStreetMap remains visible. The application does not retry or proxy blocked OSM raster tiles, spoof headers, or prefetch maps. Browser WebGL is required; if the basemap style is unavailable the route and purchase details remain visible with a notice.

Station-access 422 errors include the OSRM code, failed coordinate index when available, waypoint role/identity/coordinates and snap policy. The 75-metre restriction applies to fuel stations, not city-centroid endpoints. See [the map and Denver regression verification](docs/MAP_AND_ACCESS_FIX.md).
