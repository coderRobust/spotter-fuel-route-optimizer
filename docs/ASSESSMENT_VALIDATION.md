# Assessment validation — 25 October 2026 (India)

## Status: partial; core real multi-stop acceptance remains unresolved

No successful real multi-stop response or verified stop/purchase list can be provided. The actual API returned 422 for Chicago → Los Angeles. No fake stations or hardcoded successful responses were added. No Loom or questionnaire work was performed.

## Changes

- Fixed empty-tank refueling at mile zero and rounding accumulation in total gallons purchased.
- Added deterministic 2,000-mile multi-purchase coverage, initial-fuel and range boundaries, missing-coverage API behavior, and inaccessible/off-corridor checks.
- Added OSRM per-segment distance annotations in the existing single routing request. Projection uses those distances when available; approximate global scaling remains a fallback. Internal projection mile markers are no longer rounded before optimization.
- Excluded non-US station states from trip selection.
- Added conservative offline OSM Point POI matching with per-candidate rejection/review reasons and duplicate POI rejection. No candidate is automatically verified.
- Verified coordinate imports require source attribution, provider ID, confidence, independent evidence, reviewer, timezone-aware review timestamp and VERIFIED review status. Reject duplicate POI/coordinate assignments atomically. Historical labels are not retroactively certified.
- Added initial schema migration plus coordinate evidence migration, supporting both fresh installations and adoption of the existing syncdb-created table.
- Count duplicate/conflicting CSV price observations; preserve and document the existing optimistic lowest-price rule. Abort reimport if a verified station's name/address has changed.
- Handle malformed geocoder JSON as provider failure, hash geocoder cache keys, and avoid printing provider exceptions that can contain API keys.
- Added a real endpoint verification/benchmark script, expanded ignore rules for local geographic data, corrected external-call counts, and documented the review workflow.

## Tests and setup

Original baseline: **18 passed**. Final expanded suite: **32 passed**, including all originals. Django system check: no issues. Migration drift check: no changes detected. A separate fresh SQLite database was migrated and the source CSV imported; 8,151 source rows produced 6,738 identities, with 1,413 duplicate rows, 1,304 price conflicts and zero invalid rows. Existing local database was backed up outside the repository before applying migrations.

External calls are mocked in tests. Synthetic station fixtures demonstrate algorithm/API behavior only and are never imported as production station data. Offline matching does not certify geographic accuracy. GitHub Actions must be observed separately after a push; local checks do not establish CI success.

## Current station coverage

- Total source station identities: **6,738**.
- With coordinates: **249**.
- City-centroid approximations: **248**.
- Historical `station_verified` label: **1**, with **zero** records carrying independent review evidence.
- Unlocated US stations: **6,377**.
- Independently verified coordinates added in this run: **0**.

Public OSM corridor retrieval was attempted: the first endpoint returned HTTP 406; the alternative timed out. No provider coordinates were promoted or redistributed. Completing real station verification still requires an authorized offline POI export or accessible provider, then independent identity/location review. The matching/review process is reproducible, but a successful demonstration dataset is not yet available.

## Actual API measurement

Request: `POST /api/v1/routes/optimize/`, Chicago, IL → Los Angeles, CA, 500-mile range, 10 MPG, starting fuel 50 gallons. See [captured request and response](demo_validation.json).

| Run | HTTP | Latency | Routing calls | Geocoding calls |
| --- | --- | --- | --- | --- |
| Uncached | 422 | 4.580 s | 1 | 0 |
| Cached | 422 | 0.232 s | 0 | 0 |

Reported route: **2,018.04 miles**, **24** approximate candidates; first candidate at **1,000.62 miles**, beyond the initial 500-mile range. A 422 is the correct result for that candidate coverage. These are single-process, single-machine observations, not throughput guarantees.

## Remaining limitations

Real >1,000-mile HTTP 200 with two or more independently validated CSV stations is outstanding. Therefore there are no verified real-route gallons, station purchases or cost figures to claim. Coordinate evidence fields enforce review accountability, not independent fact-checking. Name similarity is not a calibrated confidence model. Import duplicate checks intentionally reject shared coordinates/POIs even if a real facility could host multiple records; resolve these explicitly.

The optimization remains continuous-fuel, known historical prices, fixed route, zero detour. Proximity does not establish road access; access-road detours, directionality, closures and associated fuel are unmodeled. The geometry segment projection remains an approximation on loops or repeated roads. Only contiguous-US endpoints are supported; a bounding box does not prove jurisdiction. Centroids remain approximate candidates for backwards compatibility, clearly disclosed in metadata. Price provenance remains the original committed source CSV; minimum conflicting prices are optimistic, with no freshness guarantee. Cache is process-local. Public OSRM/Nominatim have availability and usage limitations.

## Changed files

- `.gitignore`, `README.md`
- `planner/models.py`, `planner/station_matching.py`
- `planner/geography.py`, `planner/optimization.py`, `planner/services.py`, `planner/views.py`
- `planner/management/commands/import_stations.py`
- `planner/management/commands/import_station_coordinates.py`
- `planner/management/commands/match_station_pois.py`
- `planner/migrations/__init__.py`, `planner/migrations/0001_initial.py`, `planner/migrations/0002_station_coordinate_confidence_and_more.py`
- `planner/tests/test_completion.py`
- `scripts/geocode_station_candidates.py`, `scripts/verify_demo.py`
- `docs/STATION_VERIFICATION.md`, `docs/ASSESSMENT_VALIDATION.md`, `docs/demo_validation.json`
