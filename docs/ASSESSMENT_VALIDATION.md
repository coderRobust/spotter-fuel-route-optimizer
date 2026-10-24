# Assessment validation — 25 October 2026 (India)

## Technical demonstration passed; submission and coverage limits remain

The actual Chicago → Los Angeles endpoint now returns **HTTP 200**, a rendered map URL and **seven road-access-verified fuel purchases** on a **2,025.81-mile** driving route, using the supplied prices, 500-mile range and 10 MPG. The uncached request used two OSRM calls (base route plus selected station access), zero geocoding calls, and completed in 5.243 seconds; the cached repeat used zero provider calls and completed in 0.439 seconds. No successful endpoint response is hardcoded. Station preparation is reproducible offline.

This resolves the previously failing core demonstration. It does not establish full nationwide station coverage or global road-network optimality. A genuine <=5-minute Loom recording/upload and timely submission remain user actions, outside the technical scope. No employer questionnaire was edited or submitted.

## Actual requests, fuel and cost

Request: `POST /api/v1/routes/optimize/`

```json
{"start":"Chicago, IL","finish":"Los Angeles, CA","vehicle":{"max_range_miles":500,"mpg":10,"starting_fuel_gallons":50}}
```

Captured [current-schema request/response and benchmark](demo_validation.json); geometry is omitted only from the report to keep it reviewable. The API returns the full LineString and a live `map_url`. The map URL is cache-bound and expires; repeat the POST to regenerate it.

| OPIS | Station | Mile | Gallons bought | USD/gallon | Purchase USD |
| --- | --- | ---: | ---: | ---: | ---: |
| 70406 | Love's #754, Rochelle IL | 79.94 | 7.994 | 3.74900 | 29.97 |
| 67066 | Love's #361, Newton IA | 298.90 | 1.096 | 3.76233 | 4.12 |
| 66236 | Love's #309, Aurora NE | 590.90 | 50.000 | 3.28900 | 164.45 |
| 67284 | Love's #390, North Platte NE | 745.13 | 15.423 | 3.45567 | 53.30 |
| 67067 | Love's #377, Hudson CO | 977.90 | 23.276 | 3.45900 | 80.51 |
| 69291 | Love's #581, Salina UT | 1455.41 | 10.485 | 3.70567 | 38.85 |
| 66912 | Love's #335, Cedar City UT | 1582.74 | 44.307 | 3.64900 | 161.68 |

**Total:** 152.581 gallons purchased, 202.581 gallons consumed, 0.000 gallons remaining, **$532.88 additional purchase cost**. The existing starting 50 gallons are excluded from purchase cost. Prices are historical CSV observations, not today's pump prices.

All selected stations snapped within 20 meters of the returned driving route; lateral candidate offsets are 0.135–0.214 miles. The longest road-routed leg is **477.51 miles**, below the 500-mile maximum. Independent response checks validated station identity, source price, forward stop order, each leg's fuel, tank capacity, fuel balance and cost. Individual quantities are rounded for display; computations retain full precision.

OSRM selected a northern route. Nine verified candidates were available; seven were selected as purchase stops. The default access check routes through all selected fuel coordinates and recomputes fuel consumption using actual OSRM leg distances. This validates the stops in the returned plan but does not exhaustively search combinations of alternate stations.

## Measurements

Single-machine observations, not throughput/SLA guarantees:

| Real request | Purchases | HTTP | Cold latency | Warm latency | Routing calls cold/warm | Geocoding calls |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Chicago → Los Angeles | 7 | 200 | 5.243 s | 0.439 s | 2 / 0 | 0 |

Every successful response passed the independent fuel audit. The full long-route JSON was **540,567 bytes** cold; it retains accurate full-resolution geometry. Benchmark call counts wrap actual outgoing HTTP calls; they do not mock provider results. Each request can additionally use up to two geocoding calls if its text endpoints are not preset/cached.

The running Django server was also checked over real TCP HTTP: health, station stats, Swagger/schema, optimize and map all returned 200; invalid input returned 400. Headless Chrome previously rendered route geometry, seven markers (start, finish, five purchases), OSM tiles and the purchase list. The updated access-verified route was validated through the live API; browser tile/CDN requests are separate from routing calls. See `demo-map.png` for the earlier rendered map.

## Station data and reproducibility

- Original supplied CSV: **8,151 rows**, **6,738 identities**, **1,413 duplicate observations**, **1,304 conflicting-price observations**, zero invalid rows on import.
- Bundled station matches: **12** manually source-reviewed corridor locations plus **94** exact cross-source CSV/operator/OSM matches (no overlaps); these are not claimed as field visits.
- Current local database after preparation: **344** located stations, including **237** city-centroid approximations, **106** cross-source verified locations with evidence, and **one** legacy verified label without evidence. The legacy record is excluded by the default policy.
- Fresh SQLite setup: all migrations applied, **6,738** identities imported, and all **106** bundled locations prepared offline without geocoding.

Review evidence matches official operator OPIS/store/city/state/highway exits against actual OSM fuel POIs. The [reviewed subset and attribution](../data/verified_corridor/README.md) preserve OSM feature versions, source URLs and ODbL terms. Canopy polygon representative points lie inside their actual reviewed fuel footprints; selected unnamed fuel POIs are checked inside service polygons whose operator store ref/website/phone match. City centers and generic exits are not promoted to station locations. Confidence .95 is a qualitative source review judgment, not a calibrated probability or field-visit claim.

`python manage.py prepare_corridor_coordinates --apply` and `python manage.py prepare_nationwide_coordinates --apply` regenerate ignored coordinate CSVs and import them through the standard evidence/duplicate/conflict checks. Both offline preparation steps run in GitHub Actions.

## Code fixes and checks

Final local suite: **49 passed** (original baseline 18). No assertions were disabled or weakened. One original success fixture now supplies explicit verified-coordinate evidence to meet the stricter default location policy.

- Empty tank can refuel at the origin; total purchase gallons no longer accumulate per-stop rounding errors.
- Added multi-purchase, exact-range, empty-tank, missing-coverage and inaccessible/off-corridor tests; independent exhaustive DP checks greedy cost on 20 deterministic scenarios.
- Added transactional evidence imports, duplicate POI/coordinate rejection, reproducible corridor and nationwide source preparation, exact identity checks, and idempotency checks.
- Default route access verification adds a second cached OSRM request and includes selected-station detour fuel; API metadata exposes request count and access status.
- Added verified-only default selection, US state filtering, indexed bounding-box filtering and per-segment OSRM route distances. No route-position truncation drops later candidates.
- Added finite numeric validation, Alaska/Hawaii endpoint bounds, malformed provider checks and distinct 400/422/502 handling.
- Added a real rendered map with safe JSON/DOM text handling, expiry tests and shared filesystem caching across local workers.
- Updated Postman requests with success, verified-policy, fuel-balance, map and invalid-input assertions; Swagger uses the actual runtime request serializer.
- Django system check: **no issues**. Migration consistency: **no changes detected**. Fresh schema/import/preparation: **passed**. `git diff --check`: **passed**.

The final commit/push and observed GitHub Actions result are reported in the accompanying completion message. Docker commands are documented; Docker execution/production deployment is not claimed as tested.

## Exact remaining limitations

1. **Nationwide station-level enrichment is incomplete.** The 106 bundled locations are not a comprehensive US database. Many other valid US routes may return 422 because no feasible verified fuel chain is available; the API cannot promise a plan for every pair of US endpoints.
2. **Fixed-route optimization.** The default routes through the initially selected stations and accounts for detours, but does not exhaustively search all alternate station combinations. Optimality applies only to available candidates on the returned route, not all real-world alternatives. Projection can be ambiguous on loops.
3. **Historical pricing and initial fuel.** Minimum conflicting observations are optimistic; no price freshness is established. Starting fuel has no invented purchase valuation.
4. **Geography/provider bounds.** Bounding boxes are not jurisdiction polygons; roads disconnected by water legitimately return 422. Public services have rate/availability limits. Live Alaska/Hawaii routes were not demonstrated, although inputs validate.
5. **Local deployment scope.** File cache supports local workers on the same filesystem; distributed deployment requires suitable shared infrastructure. Public Leaflet CDN/OSM tiles are needed for the interactive basemap. DEBUG/secrets/TLS/hosting must be configured for production.
6. **Loom and submission.** User must record/upload the real <=5-minute Postman/code demonstration and submit GitHub/Loom links within the employer's deadline. Receipt time was not provided, so deadline compliance cannot be certified.

## Files changed during the initial assessment implementation

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
