def fuel_gap_diagnostics(stations, distance_miles, max_range):
    positions = [0.0]

    for station in stations:
        pos = float(station["route_mile"])
        if 0 < pos < float(distance_miles):
            positions.append(pos)

    positions.append(float(distance_miles))
    positions = sorted(set(positions))

    gaps = []

    for start, finish in zip(positions, positions[1:]):
        distance = finish - start

        if distance > float(max_range) + 0.000001:
            gaps.append({
                "from_mile": round(start, 2),
                "to_mile": round(finish, 2),
                "gap_miles": round(distance, 2),
            })

    return {
        "candidate_stations": len(stations),
        "largest_gap_miles": round(
            max(
                (b - a for a, b in zip(positions, positions[1:])),
                default=0,
            ),
            2,
        ),
        "gaps_over_vehicle_range": gaps[:20],
    }
