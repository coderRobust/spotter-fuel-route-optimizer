# Suggested Loom script (maximum 5 minutes)
0:00–0:30: State assessment requirements; describe fixed-route optimization and price dataset.
0:30–1:20: Show `GET /health/`, `GET /api/v1/stations/stats/`, and POST optimize using Postman.
1:20–2:10: Highlight GeoJSON route geometry, stop details, gallons and fuel total. Explain tank starts full in sample.
2:10–3:00: Show optimizer and comparison with a naive cheapest-near-500-mile strategy; explain next-cheaper-price logic.
3:00–3:50: Show provider wrapper, one route request, route caching, station preprocessing. Explain geocoding may make additional calls.
3:50–4:25: Run pytest and demonstrate input validation / unserviceable route.
4:25–5:00: Discuss missing station GPS, city-centroid approximation, zero-detour assumption, scale-out improvements, and ethical limits of results.
Record a REAL working request; do not claim tests or benchmark numbers without running them.
