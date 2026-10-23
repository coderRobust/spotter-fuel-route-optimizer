# Assessment requirement traceability
| Requirement | Implementation | Limitations |
| --- | --- | --- |
| Latest stable Django | Django 6.1.2 pin | Python 3.12+ required |
| US start and finish | DRF POST with place strings or coordinates | Bounding box not complete geographical validation |
| Driving route and map | OSRM GeoJSON LineString | No rendered HTML map; API consumer can display GeoJSON |
| Lowest-cost fuel stops | Fixed-route greedy optimized purchase quantities | City-centroid and zero-detour approximation |
| 500 mile max / 10 MPG | Defaults in serializer and optimizer | Starting fuel assumed full unless provided |
| USD fuel price | Original CSV imported | Duplicate prices resolved by choosing minimum |
| Fast API and routing calls | One OSRM route call, bounded cache | Geocoding call possible, cold latency not benchmarked |
| GitHub source | Included ZIP to initialize personal GitHub repo | Not uploaded |
| Loom <=5 minutes | Recording script | Not recorded |
| Submission in three days | README and project files | User must submit |
