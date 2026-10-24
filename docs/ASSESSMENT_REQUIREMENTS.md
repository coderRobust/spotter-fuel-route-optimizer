# Employer requirement traceability

| Requirement | Evidence | Remaining boundary |
| --- | --- | --- |
| Latest stable Django | Django 6.1.2; official download page checked 25 October 2026 | Verify again if submitting substantially later |
| US start/finish | Place names or coordinates, bounds including AK/HI; invalid inputs rejected | Bounds alone do not establish jurisdiction; disconnected roads return 422 |
| Route/map and stops | OSRM GeoJSON plus rendered `map_url`; headless Chrome rendering checked | Map uses external Leaflet assets and OSM tiles; private cache tokens expire |
| Cost-effective CSV stations | Decimal greedy optimizer; independent exhaustive oracle comparisons; 12 source-reviewed stations plus 94 exact cross-source CSV/operator/OSM matches | Optimizes available candidates on the fixed route; default routes through selected stops and accounts for detour fuel; incomplete nationwide coverage |
| 500 miles / 10 MPG | Default model; exact range, empty tank, multiple-purchase tests and real response fuel audits | Initial tank defaults full; its existing cost is excluded explicitly |
| Multiple fuel stops and total cost | Real Chicago–Los Angeles: 2,025.81 miles, 7 road-access-verified purchases, $532.88 | Historical prices, no freshness guarantee; existing tank fuel excluded |
| Fast response / few provider calls | Cold/warm measurements, 2/0 routing calls; presets require no geocoding | Up to 2 additional calls for uncached endpoint geocoding; map tile calls are separate |
| Reproducible GitHub source | Migrations, original price CSV, ODbL-attributed OSM match data, CI clean preparation/test steps | Public routing service must be available for live demo |
| <=5-minute Loom | Existing recording outline and runnable Postman collection | User still needs to record/upload a genuine Loom; excluded from technical scope |
| Submit within 3 days | Repository and validation report ready for review | Receipt date unknown; user must submit links on time |

See [execution evidence and exact remaining limitations](ASSESSMENT_VALIDATION.md).
