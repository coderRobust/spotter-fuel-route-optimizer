import unittest

from planner.optimization import (
    optimize_fuel_stops,
    UnreachableRoute,
)


class ExtendedOptimizerTests(unittest.TestCase):

    @staticmethod
    def station(mile, price):
        return {
            "route_mile": mile,
            "price": price,
            "opis_id": str(mile),
            "name": f"Station {mile}",
        }

    def test_initial_five_gallons_reaches_station(self):
        result = optimize_fuel_stops(
            stations=[
                self.station(30, 3.40),
                self.station(100, 3.10),
            ],
            distance_miles=180,
            max_range=500,
            mpg=10,
            starting_fuel=5,
        )

        self.assertGreater(
            result["total_gallons_purchased"], 0
        )
        self.assertAlmostEqual(
            result["total_gallons_consumed"], 18
        )
        self.assertAlmostEqual(
            result["total_cost_usd"], 41.8,
            places=2,
        )

    def test_first_station_beyond_initial_range(self):
        with self.assertRaises(UnreachableRoute):
            optimize_fuel_stops(
                stations=[self.station(60, 3.0)],
                distance_miles=180,
                max_range=500,
                mpg=10,
                starting_fuel=5,
            )

    def test_exact_initial_range_boundary(self):
        result = optimize_fuel_stops(
            stations=[self.station(50, 3.0)],
            distance_miles=180,
            max_range=500,
            mpg=10,
            starting_fuel=5,
        )

        self.assertAlmostEqual(
            result["total_gallons_purchased"], 13
        )
        self.assertAlmostEqual(
            result["total_cost_usd"], 39
        )

    def test_no_stops_when_starting_fuel_suffices(self):
        result = optimize_fuel_stops(
            stations=[],
            distance_miles=180,
            max_range=500,
            mpg=10,
            starting_fuel=50,
        )

        self.assertEqual(result["stops"], [])
        self.assertEqual(
            result["total_cost_usd"], 0
        )


if __name__ == "__main__":
    unittest.main()
