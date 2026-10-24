# Independently reviewed demonstration corridor

Twelve assessment CSV stations were matched by OPIS ID, store number, city/state and original highway exit against the operator's public listings on 25 October 2026 (India). Coordinates come from actual OpenStreetMap fuel POIs, independently cross-checked against the operator's street address and directions. Operator pages are linked in `manifest.json`; no operator prices, page dumps or proprietary coordinate databases are redistributed. Fuel prices always come from the supplied assessment CSV.

`osm_fuel_features.geojson` is a small extract from **© OpenStreetMap contributors**, available under **ODbL 1.0**: https://opendatacommons.org/licenses/odbl/1-0/ . Attribution and OSM feature version/timestamp are preserved. Source: https://api.openstreetmap.org/api/0.6/map . Individual feature links are reconstructible as `https://www.openstreetmap.org/{id}`. This derived OSM database is offered under the same ODbL terms; the application source license is unaffected.

For reviewed polygon POIs (Rolla, Amarillo, Kingman, Aurora, Salina and Las Vegas), the representative location is the area centroid of the specifically reviewed diesel fuel-canopy footprint, not the centroid of a city, generic exit or entire travel plaza. For Albuquerque the exact fuel node has the operator's street address. Oklahoma City and Joplin fuel nodes sit within operator-matched service-area polygons whose store reference, official website and phone match the official listing. The service polygons are included to make these checks reviewable. A generic name-only highway match would not be enough.

Matching records:

| OPIS | Store | Location | Fuel POI | Independent identity check |
| --- | --- | --- | --- | --- |
| 66937 | 341 | Rolla, MO | way/677336597 | Official OPIS, I-44 exit 189, matching 3500 Hy Point Industrial Park Drive and OSM website |
| 4227 | 203 | Oklahoma City, OK | node/1923797592 | Official OPIS, I-40 exit 140, service polygon way/226293091 ref 203/website/phone |
| 4446 | 200 | Amarillo, TX | way/221639649 | Official OPIS 04446, I-40 exit 74, operator directions at the same Love's canopy facility |
| 2922 | 210 | Albuquerque, NM | node/1678893882 | Official OPIS 02922, I-40 exit 158, matching 2200 6th Street NW |
| 66040 | 272 | Kingman, AZ | way/223539583 | Official OPIS, I-40 exit 59, matching 6035 East Minerva Lane, phone and OSM website |
| 64481 | 282 | Joplin, MO | node/12249854436 | Official OPIS, I-44 exit 4, service polygon way/226181120 ref 282/website/phone |

Additional stations along the actual OSRM northern route:

| OPIS | Store | Location | Fuel POI | Independent identity check |
| --- | --- | --- | --- | --- |
| 67066 | 361 | Newton, IA | node/947850836 | Official OPIS, I-80 exit 168; containing way/225360873 matches store ref/website/phone |
| 66236 | 309 | Aurora, NE | way/225056801 | Official OPIS, I-80 exit 332; containing way/225056798 matches store ref/website/phone |
| 67067 | 377 | Hudson, CO | node/4182375319 | Official OPIS, I-76 exit 31; exact 201 East Bison Highway and phone |
| 69142 | 517 | Grand Junction, CO | node/14017650084 | Official OPIS, I-70 exit 26; containing way/414412486 matches store ref/website/phone |
| 69291 | 581 | Salina, UT | way/494917451 | Official OPIS, I-70 exit 56; exact 1915 South State Street and phone |
| 67296 | 340 | Las Vegas, NV | way/225364820 | Official OPIS, I-15 exit 64; exact 12501 Apex Great Basin Way |

Reproduce offline after importing prices:

```sh
python manage.py prepare_corridor_coordinates
python manage.py prepare_corridor_coordinates --apply
```

This rebuilds the ignored verified-coordinate CSV, then uses the normal dry-run/transactional coordinate importer. The source review manifest is curated data, not a production endpoint special case; any independently reviewed station can use the same importer. The endpoint never hardcodes these station IDs or a successful result. Confidence .95 is a qualitative review assessment, not a calibrated probability. No human field visit or road-access routing is claimed.

The twelve-station subset supports the demonstrated northern corridor and an additional southern corridor; nationwide station-level coverage remains limited. Other trips may return 422 honestly. Recheck OSM/operator sources when facilities change.
