from math import atan2, cos, radians, sin, sqrt

MILES_PER_KM = 0.621371192
EARTH_MI = 3958.7613


def distance_miles(a, b):
    lat1, lon1 = map(radians, a)
    lat2, lon2 = map(radians, b)
    x = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2)
        * sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_MI * atan2(
        sqrt(x), sqrt(max(0, 1 - x))
    )


def route_candidates(points, stations, corridor=15, limit=150):
    if len(points) < 2:
        return []

    xy = [(float(p[1]), float(p[0])) for p in points]

    lengths = [
        distance_miles(a, b)
        for a, b in zip(xy, xy[1:])
    ]

    cumulative = [0.0]
    for length in lengths:
        cumulative.append(cumulative[-1] + length)

    corridor = float(corridor)
    margin_lat = corridor / 69.0

    # Broad route-level bounding box.
    min_lat = min(p[0] for p in xy)
    max_lat = max(p[0] for p in xy)
    min_lon = min(p[1] for p in xy)
    max_lon = max(p[1] for p in xy)

    # Conservative longitude margin for US routes.
    max_abs_lat = min(
        85.0, max(abs(min_lat), abs(max_lat))
    )
    lon_scale = max(0.01, cos(radians(max_abs_lat)))
    margin_lon = corridor / (69.0 * lon_scale)

    segments = []
    for i, (a, b) in enumerate(zip(xy, xy[1:])):
        segments.append((
            i, a, b,
            min(a[0], b[0]) - margin_lat,
            max(a[0], b[0]) + margin_lat,
            min(a[1], b[1]) - margin_lon,
            max(a[1], b[1]) + margin_lon,
        ))

    out = []

    for station in stations:
        if station.get("latitude") is None:
            continue
        if station.get("longitude") is None:
            continue

        s = (
            float(station["latitude"]),
            float(station["longitude"]),
        )

        # Skip distant stations immediately.
        if not (
            min_lat - margin_lat <= s[0] <= max_lat + margin_lat
            and min_lon - margin_lon <= s[1] <= max_lon + margin_lon
        ):
            continue

        best = None

        for i, a, b, la, ha, lo, hi in segments:
            if not (la <= s[0] <= ha and lo <= s[1] <= hi):
                continue

            lat0 = radians((a[0] + b[0] + s[0]) / 3)
            scale = 69.172 * cos(lat0)

            dx = (b[1] - a[1]) * scale
            dy = (b[0] - a[0]) * 69.0
            denom = dx * dx + dy * dy

            if denom:
                t = max(0.0, min(1.0, (
                    (s[1] - a[1]) * scale * dx
                    + (s[0] - a[0]) * 69.0 * dy
                ) / denom))
            else:
                t = 0.0

            near = (
                a[0] + t * (b[0] - a[0]),
                a[1] + t * (b[1] - a[1]),
            )

            lateral = distance_miles(s, near)

            if best is None or lateral < best[0]:
                best = (
                    lateral,
                    cumulative[i] + t * lengths[i],
                )

        if best and best[0] <= corridor:
            out.append({
                **station,
                "route_mile": round(best[1], 3),
                "offset_miles": round(best[0], 3),
            })

    # Preserve existing ordering and candidate limit.
    return sorted(
        out,
        key=lambda x: (x["route_mile"], x["price"])
    )[:limit]
