# Cross-source checked station matches

`validated_matches.json` bundles 94 distinct fuel-station coordinates that match the assessment CSV station identity, an official operator store reference, and an OpenStreetMap fuel POI. Matching also checks the US country and state. The coordinates are actual OSM fuel points, not city-centroid geocodes. The automated checks are reproducible identity validation, not field visits or independent road-access verification.

The records include Geoapify attribution and OpenStreetMap contributor attribution. OSM-derived data is provided under ODbL 1.0: <https://opendatacommons.org/licenses/odbl/1-0/>. Official operator store codes and source hash/date are recorded in the JSON. The application still takes prices only from `data/fuel-prices-for-be-assessment.csv`.

After importing the assessment prices, prepare and transactionally import these matches offline:

```sh
python manage.py prepare_nationwide_coordinates
python manage.py prepare_nationwide_coordinates --apply
```

The first command writes a review CSV and performs a dry run. The second applies the same identity, duplicate, and evidence checks used by the shared coordinate importer. It makes no network requests and stores the generated CSV under the ignored `data/geocoding/` directory by default.

These 94 locations expand the separate 12-location corridor dataset but do not provide comprehensive US coverage. Routes with insufficient verified stations return HTTP 422 rather than claiming an unsupported fuel plan.
