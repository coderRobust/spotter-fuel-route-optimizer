# Suggested Loom script (maximum 5 minutes)
0:00–0:30: State assessment requirements; describe fixed-route optimization, the supplied price dataset, and the verified station subset.
0:30–1:20: Show `GET /health/`, `GET /api/v1/stations/stats/`, and POST optimize using Postman.
1:20–2:10: Highlight GeoJSON route geometry, road-access-verified stop details, gallons and fuel total. Explain tank starts full in sample and that starting fuel cost is excluded.
2:10–3:00: Show optimizer and comparison with a naive cheapest-near-500-mile strategy; explain next-cheaper-price logic and that the selected-stop reroute is not a global optimum.
3:00–3:50: Show provider wrapper, two uncached routing requests (base route and selected-stop access), route caching, and offline station preprocessing. Explain uncached text endpoints may make additional geocoding calls.
3:50–4:25: Run pytest and demonstrate input validation / unserviceable route.
4:25–5:00: Discuss incomplete nationwide coverage, historical prices, alternate-stop search limitations, scale-out improvements, and honest limits of results.
Record a REAL working request; do not claim tests or benchmark numbers without running them.
