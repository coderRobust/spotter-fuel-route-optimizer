def fuel_gap_diagnostics(
    stations,
    distance_miles,
    max_range,
    mpg=10,
    starting_fuel=None,
):
    distance_miles = float(distance_miles)
    max_range = float(max_range)
    mpg = float(mpg)

    capacity = max_range / mpg
    initial_fuel = capacity if starting_fuel is None else float(starting_fuel)
    initial_range = initial_fuel * mpg

    positions = sorted({
        float(station["route_mile"])
        for station in stations
        if 0 < float(station["route_mile"]) < distance_miles
    })

    points = [0.0, *positions, distance_miles]
    legs = [
        {"from_mile": round(a, 2),
         "to_mile": round(b, 2),
         "gap_miles": round(b-a, 2)}
        for a, b in zip(points, points[1:])
    ]

    first_target = positions[0] if positions else distance_miles

    return {
        "candidate_stations": len(stations),
        "initial_fuel_gallons": round(initial_fuel, 3),
        "initial_range_miles": round(initial_range, 2),
        "first_station_mile": round(positions[0], 2) if positions else None,
        "first_target_reachable": first_target <= initial_range + 1e-6,
        "largest_gap_miles": round(
            max((b-a for a, b in zip(points, points[1:])), default=0),
            2,
        ),
        "gaps_over_vehicle_range": [
            leg for leg in legs if leg["gap_miles"] > max_range + 1e-6
        ][:20],
    }
