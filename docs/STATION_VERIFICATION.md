# Reproducible station verification

A reviewed twelve-station demonstration dataset is now bundled: see [source evidence and ODbL attribution](../data/verified_corridor/README.md). After importing prices, run `python manage.py prepare_corridor_coordinates --apply` to reproduce it offline. The generic workflow below remains available for further enrichment. City centroids and historical labels without evidence do not establish station-level accuracy.

1. Create the environment, install requirements, migrate, and run `python manage.py import_stations`.
2. Obtain an authorized local OpenStreetMap fuel POI export for the demonstration corridor (IL, MO, OK, TX, NM, AZ, CA). Preserve the source URL, download date, dataset version/hash and OpenStreetMap contributor attribution. Respect ODbL and the supplier's usage limits. This command makes no external calls and does not bulk-query Nominatim.
3. Supply a GeoJSON FeatureCollection of Point features with OSM tags in `properties`, including `amenity=fuel`, `name`/`brand`, `addr:city`, `addr:state`, `addr:housenumber`, `addr:street`, and an OSM element ID in `id`. Non-point features must be checked and converted upstream; arbitrary polygon centers are not accepted by this matcher.
4. Run `python manage.py match_station_pois --geojson /path/fuel.geojson --states IL,MO,OK,TX,NM,AZ,CA --output data/geocoding/osm_review.csv` (create the output directory first). Candidates have name similarity scores, not calibrated geographic confidence. Missing address/city tags reduce coverage intentionally. Multiple assignments of a POI are rejected.
5. Independently inspect operator location listings and map evidence. Match the original CSV identity, store number, brand, city/state, original address or documented highway exit, and actual forecourt location. A city center, generic exit or different brand is insufficient. Highway descriptions require manual resolution and remain rejected by automatic address matching. Resolve conflicting POI assignments before proceeding.
6. Create `data/verified_station_coordinates.csv` only for validated records, with the exact header below. `address` must remain the original CSV address; `provider_id` identifies the POI, never an inferred OPIS ID. `evidence` must document independently checked sources and the identity/exit resolution. `reviewed_at` must be an ISO timestamp with timezone. `reviewer` identifies the responsible reviewer. The importer checks evidence fields; it cannot prove that a reviewer actually inspected their sources.

```csv
opis_id,city,state,address,latitude,longitude,provider,provider_id,confidence,review_status,evidence,reviewer,reviewed_at
```

7. Dry-run `python manage.py import_station_coordinates --csv data/verified_station_coordinates.csv`, then repeat with `--apply`. Invalid rows abort the entire import. Provider attribution, confidence, evidence, reviewer and timestamp are stored in the database. Existing verified coordinates cannot be silently moved.
8. Run `python scripts/verify_demo.py` with network access. It invokes the actual endpoint, reports HTTP status, additional fuel cost, measured latency, and routing/geocoding calls for uncached and cached requests. A 422 means demonstrated coverage is insufficient; do not substitute a precomputed success.

Provider inputs, review reports and verified coordinate files are ignored by Git pending redistribution review. The reviewed OSM corridor subset is deliberately redistributable under ODbL with contributor attribution. A fresh clone can reproduce the demonstrated station preparation offline. Nationwide enrichment remains incomplete.

# Database migration

Fresh installations: `python manage.py migrate --noinput`.

Legacy installations whose tables were created using `--run-syncdb`: back up the database and use `python manage.py migrate --fake-initial --noinput` once. Migration 0001 adopts the existing Station table; migration 0002 adds review evidence fields. Do not fake migration 0002.
