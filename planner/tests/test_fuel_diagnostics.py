from planner.diagnostics import fuel_gap_diagnostics


def test_starting_fuel_diagnostic():
    result = fuel_gap_diagnostics(
        [{"route_mile": 60, "price": 3.0}],
        distance_miles=180,
        max_range=500,
        mpg=10,
        starting_fuel=5,
    )
    assert result["initial_range_miles"] == 50
    assert result["first_station_mile"] == 60
    assert result["first_target_reachable"] is False


def test_reachable_first_station():
    result = fuel_gap_diagnostics(
        [{"route_mile": 30, "price": 3.0}],
        distance_miles=180,
        max_range=500,
        mpg=10,
        starting_fuel=5,
    )
    assert result["first_target_reachable"] is True


def test_full_tank_defaults():
    result = fuel_gap_diagnostics(
        [], distance_miles=180, max_range=500, mpg=10
    )
    assert result["initial_range_miles"] == 500
    assert result["first_target_reachable"] is True


def test_large_interstation_gap():
    result = fuel_gap_diagnostics(
        [{"route_mile": 100}, {"route_mile": 750}],
        distance_miles=900, max_range=500, mpg=10,
    )
    assert result["largest_gap_miles"] == 650
    assert result["gaps_over_vehicle_range"][0]["from_mile"] == 100
