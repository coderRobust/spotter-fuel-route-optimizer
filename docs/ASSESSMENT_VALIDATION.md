# Assessment validation — 25 October 2026 (India)

## Technical demonstration passed; submission and coverage limits remain

The actual Chicago → Los Angeles endpoint now returns **HTTP 200**, a rendered map URL and **five geographically credible fuel purchases** on a **2,018.04-mile** driving route, using the supplied prices, 500-mile range and 10 MPG. No successful endpoint response is hardcoded. External routing is real; station data is independently source-checked. A fresh clone can reproduce the twelve-station preparation offline.

This resolves the previously failing core demonstration. It does not establish full nationwide station coverage or global road-network optimality. A genuine <=5-minute Loom recording/upload and timely submission remain user actions, outside the technical scope. No employer questionnaire was edited or submitted.

## Actual requests, fuel and cost

Request: `POST /api/v1/routes/optimize/`

```json
{"start":"Chicago, IL","finish":"Los Angeles, CA","vehicle":{"max_range_miles":500,"mpg":10,"starting_fuel_gallons":50}}
```

Captured [current-schema request/response and benchmark](demo_validation.json); geometry is omitted only from the report to keep it reviewable. The API returns the full LineString and a live `map_url`. The map URL is cache-bound and expires; repeat the POST to regenerate it.

| OPIS | Station | Mile | Gallons bought | USD/gallon | Purchase USD |
| --- | --- | ---: | ---: | ---: | ---: |
| 67066 | Love's #361, Newton IA | 296.71 | 8.763 | 3.76233 | 32.97 |
| 66236 | Love's #309, Aurora NE | 587.63 | 50.000 | 3.28900 | 164.45 |
| 67067 | Love's #377, Hudson CO | 972.20 | 38.457 | 3.45900 | 133.02 |
| 69291 | Love's #581, Salina UT | 1448.97 | 25.495 | 3.70567 | 94.48 |
| 67296 | Love's #340, Las Vegas NV | 1727.15 | 29.089 | 3.68900 | 107.31 |

**Total:** 151.804 gallons purchased, 201.804 gallons consumed, 0.000 gallons remaining, **$532.23 additional purchase cost**. The existing starting 50 gallons are excluded from purchase cost. Prices are historical CSV observations, not today's pump prices.

Selected station lateral offsets are 0.135–0.237 miles from the road polyline. The largest gap between actual purchases is approximately **476.77 miles**, below 500. Independent response checks validated station identity, source price, forward stop order, each leg's fuel, tank capacity, fuel balance and cost. Individual quantities are rounded for display; computations retain full precision.

OSRM selected **I-80/I-76/I-70/I-15**, not the initially assumed southern corridor. The endpoint uses the returned geometry; it does not force the demonstration past its prepared stations. The northern route has six verified candidates; the optimizer skips the more expensive Grand Junction purchase when it is unnecessary.

## Measurements

Single-machine observations, not throughput/SLA guarantees:

| Real request | Purchases | HTTP | Cold latency | Warm latency | Routing calls cold/warm | Geocoding calls |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Chicago → Oklahoma City | 1 | 200 | 4.857 s | 0.144 s | 1 / 0 | 0 |
| Chicago → Denver | 2 | 200 | 4.523 s | 0.134 s | 1 / 0 | 0 |
| Chicago → Los Angeles | 5 | 200 | 4.986 s | 0.213 s | 1 / 0 | 0 |

[One- and two-purchase execution records](real_route_checks.json). Every successful response passed the independent fuel audit. The full long-route JSON was **529,532 bytes** cold; it retains accurate full-resolution geometry. Benchmark call counts wrap actual outgoing HTTP calls; they do not mock provider results. Each request can additionally use up to two geocoding calls if its text endpoints are not preset/cached.

The running Django server was also checked over real TCP HTTP: health, station stats, Swagger/schema, optimize and map all returned 200; invalid input returned 400. Headless Chrome rendered route geometry, seven markers (start, finish, five purchases), OSM tiles and the purchase list. Opening the map issues no new routing request; browser tile/CDN requests are separate. See `demo-map.png` for the actual rendered screenshot.

## Station data and reproducibility

- Original supplied CSV: **8,151 rows**, **6,738 identities**, **1,413 duplicate observations**, **1,304 conflicting-price observations**, zero invalid rows on import.
- Independently reviewed station locations: **12** across the northern and southern demonstration corridors.
- Existing local database after enrichment: **253** coordinates, including **240** city-centroid approximations and **one** historical verified label without review evidence. These legacy records are excluded by the default policy.
- Fresh SQLite setup: all migrations applied, **6,738** identities imported, **12** independently reviewed locations prepared from bundled OSM geometry without external geocoding.

Review evidence matches official operator OPIS/store/city/state/highway exits against actual OSM fuel POIs. The [reviewed subset and attribution](../data/verified_corridor/README.md) preserve OSM feature versions, source URLs and ODbL terms. Canopy polygon representative points lie inside their actual reviewed fuel footprints; selected unnamed fuel POIs are checked inside service polygons whose operator store ref/website/phone match. City centers and generic exits are not promoted to station locations. Confidence .95 is a qualitative source review judgment, not a calibrated probability or field-visit claim.

`python manage.py prepare_corridor_coordinates --apply` regenerates the ignored verified CSV and imports it through the standard evidence/duplicate/conflict checks. Fresh installation and preparation are now also GitHub Actions steps.

## Code fixes and checks

Final local suite: **39 passed** (original baseline 18). No assertions were disabled or weakened. One original success fixture now supplies explicit verified-coordinate evidence to meet the stricter default location policy.

- Empty tank can refuel at the origin; total purchase gallons no longer accumulate per-stop rounding errors.
- Added multi-purchase, exact-range, empty-tank, missing-coverage and inaccessible/off-corridor tests; independent exhaustive DP checks greedy cost on 20 deterministic scenarios.
- Added transactional evidence imports, duplicate POI/coordinate rejection, reproducible source preparation and idempotency checks.
- Added verified-only default selection, US state filtering, indexed bounding-box filtering and per-segment OSRM route distances. No route-position truncation drops later candidates.
- Added finite numeric validation, Alaska/Hawaii endpoint bounds, malformed provider checks and distinct 400/422/502 handling.
- Added a real rendered map with safe JSON/DOM text handling, expiry tests and shared filesystem caching across local workers.
- Updated Postman requests with success, verified-policy, fuel-balance, map and invalid-input assertions; Swagger uses the actual runtime request serializer.
- Django system check: **no issues**. Migration consistency: **no changes detected**. Fresh schema/import/preparation: **passed**. `git diff --check`: **passed**.

The final commit/push and observed GitHub Actions result are reported in the accompanying completion message. Docker commands are documented; Docker execution/production deployment is not claimed as tested.

## Exact remaining limitations

1. **Nationwide station-level enrichment is incomplete.** Twelve reviewed stations are a reproducible demonstration subset. Many other valid US routes may return 422 because no feasible verified fuel chain is available; the API cannot promise a plan for every pair of US endpoints.
2. **Fixed-route, zero-detour optimization.** Ramps/access roads, directionality, closures and detour fuel are not independently road-routed. Optimality applies to available candidates in this model, not all real-world alternatives. Projection can be ambiguous on loops. The demonstration keeps provider calls to one, rather than claiming verified detour modeling.
3. **Historical pricing and initial fuel.** Minimum conflicting observations are optimistic; no price freshness is established. Starting fuel has no invented purchase valuation.
4. **Geography/provider bounds.** Bounding boxes are not jurisdiction polygons; roads disconnected by water legitimately return 422. Public services have rate/availability limits. Live Alaska/Hawaii routes were not demonstrated, although inputs validate.
5. **Local deployment scope.** File cache supports local workers on the same filesystem; distributed deployment requires suitable shared infrastructure. Public Leaflet CDN/OSM tiles are needed for the interactive basemap. DEBUG/secrets/TLS/hosting must be configured for production.
6. **Loom and submission.** User must record/upload the real <=5-minute Postman/code demonstration and submit GitHub/Loom links within the employer's deadline. Receipt time was not provided, so deadline compliance cannot be certified.

## Complete changed-file list for this completion pass

- `.dockerignore`
- `.github/workflows/ci.yml`
- `.gitignore`
- `README.md`
- `config/settings.py`
- `config/urls.py`
- `data/verified_corridor/README.md`
- `data/verified_corridor/manifest.json`
- `data/verified_corridor/osm_fuel_features.geojson`
- `docs/ASSESSMENT_REQUIREMENTS.md`
- `docs/ASSESSMENT_VALIDATION.md`
- `docs/STATION_VERIFICATION.md`
- `docs/VSCODE_WINDOWS_STEP_BY_STEP.md`
- `docs/demo-map.png`
- `docs/demo_validation.json`
- `docs/real_route_checks.json`
- `planner/management/commands/import_station_coordinates.py`
- `planner/management/commands/prepare_corridor_coordinates.py`
- `planner/maps.py`
- `planner/optimization.py`
- `planner/serializers.py`
- `planner/services.py`
- `planner/swagger_schemas.py`
- `planner/templates/planner/route_map.html`
- `planner/tests/test_api.py`
- `planner/tests/test_completion.py`
- `planner/views.py`
- `postman_collection.json`
- `scripts/verify_demo.py`
