import csv
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from planner.models import Station
from planner.optimization import optimize_fuel_stops, UnreachableRoute
from planner.station_matching import match_candidate


class OptimizerCompletionTests(TestCase):
    def test_empty_tank_can_buy_at_origin(self):
        result = optimize_fuel_stops([{'route_mile': 0, 'price': 3}], 500, starting_fuel=0)
        self.assertEqual(result['total_gallons_purchased'], 50)
        self.assertEqual(result['total_cost_usd'], 150)

    def test_multiple_purchases_unsorted_and_exact_range(self):
        stations = [{'route_mile': mile, 'price': price} for mile, price in [(1500, 5), (500, 3), (1000, 4)]]
        result = optimize_fuel_stops(stations, 2000)
        self.assertEqual([s['mile_marker'] for s in result['stops']], [500, 1000, 1500])
        self.assertEqual(result['total_gallons_purchased'], 150)
        self.assertEqual(result['total_gallons_consumed'], 200)
        self.assertEqual(result['total_cost_usd'], 600)
        self.assertEqual(result['final_fuel_gallons'], 0)

    def test_missing_middle_station_is_infeasible(self):
        with self.assertRaises(UnreachableRoute):
            optimize_fuel_stops([{'route_mile': 500, 'price': 3}, {'route_mile': 1500, 'price': 3}], 2000)

    def test_purchase_total_rounded_once(self):
        result = optimize_fuel_stops([{'route_mile': p, 'price': v} for p, v in [(1, 3), (2.004, 2), (3.008, 1)]], 4.012, starting_fuel=.1)
        self.assertEqual(result['total_gallons_purchased'], .301)


class CoordinateImportTests(TestCase):
    def setUp(self):
        self.station = Station.objects.create(opis_id='123', name='Test Fuel', address='123 Main St', city='Test', state='AZ', price=3)
        self.row = dict(opis_id='123', city='Test', state='AZ', address='123 Main St', latitude=35, longitude=-111,
                        provider='test', provider_id='node/1', confidence=.95, review_status='VERIFIED',
                        evidence='Independent operator listing checked against POI', reviewer='reviewer', reviewed_at='2026-10-25T00:00:00Z')

    def run_import(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'coordinates.csv'
            with path.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=self.row.keys())
                writer.writeheader()
                writer.writerows(rows)
            call_command('import_station_coordinates', csv=str(path), apply=True)

    def test_verified_import_preserves_evidence(self):
        self.run_import([self.row])
        self.station.refresh_from_db()
        self.assertEqual(self.station.coordinate_provider_id, 'node/1')
        self.assertEqual(self.station.precision, 'station_verified')

    def test_unreviewed_or_mismatched_import_is_atomic(self):
        for change in [{'review_status': 'UNVERIFIED'}, {'address': 'highway exit'}, {'confidence': 'nan'}, {'reviewed_at': '2026-10-25'}]:
            with self.assertRaises(CommandError):
                self.run_import([{**self.row, **change}])
        self.station.refresh_from_db()
        self.assertIsNone(self.station.latitude)

    def test_duplicate_assignment_rejected(self):
        Station.objects.create(opis_id='456', name='Other', address='456 Main St', city='Test', state='AZ', price=3)
        with self.assertRaises(CommandError):
            self.run_import([self.row, {**self.row, 'opis_id': '456', 'address': '456 Main St'}])
        self.assertEqual(Station.objects.filter(precision='station_verified').count(), 0)

    def test_matching_never_auto_verifies(self):
        feature = {'id': 'node/1', 'geometry': {'type': 'Point', 'coordinates': [-111, 35]},
                   'properties': {'amenity': 'fuel', 'name': 'Test Fuel', 'addr:state': 'AZ', 'addr:city': 'Test', 'addr:housenumber': '123', 'addr:street': 'Main St'}}
        station = {'name': 'Test Fuel', 'address': '123 Main St', 'city': 'Test', 'state': 'AZ'}
        self.assertEqual(match_candidate(station, feature)['review_status'], 'REVIEW_REQUIRED')
        feature['properties']['name'] = 'Other Brand'
        self.assertEqual(match_candidate(station, feature)['review_status'], 'REJECTED')
        feature['properties']['name'] = 'Test Fuel'
        feature['properties']['addr:street'] = 'Exit 20'
        self.assertEqual(match_candidate(station, feature)['review_status'], 'REJECTED')


class LongRouteApiTests(TestCase):
    @patch('planner.views.get_route')
    def test_long_route_success_and_missing_coverage(self, route_mock):
        route_mock.return_value = ({'distance_miles': 2000, 'duration_minutes': 2000,
                                    'geometry': {'type': 'LineString', 'coordinates': [[-90, 35], [-95, 35], [-100, 35], [-105, 35], [-110, 35]]}}, False)
        for n, lon in enumerate([-95, -100, -105]):
            Station.objects.create(opis_id=str(n), name='Synthetic test fixture', city='Test', state='NM', price=3,
                                   latitude=35, longitude=lon)
        payload = {'start_coordinates': {'lat': 35, 'lon': -90}, 'finish_coordinates': {'lat': 35, 'lon': -110}}
        response = APIClient().post('/api/v1/routes/optimize/', payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertGreaterEqual(len(response.data['fuel_plan']['stops']), 3)
        Station.objects.all().delete()
        response = APIClient().post('/api/v1/routes/optimize/', payload, format='json')
        self.assertEqual(response.status_code, 422)

    @patch('planner.views.get_route')
    def test_non_us_station_excluded(self, route_mock):
        route_mock.return_value = ({'distance_miles': 700, 'geometry': {'coordinates': [[-100, 35], [-110, 35]]}}, False)
        Station.objects.create(opis_id='ca', name='Non-US', city='Test', state='ON', price=3, latitude=35, longitude=-105)
        response = APIClient().post('/api/v1/routes/optimize/', {'start': 'Chicago, IL', 'finish': 'Los Angeles, CA'}, format='json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data['candidate_stations'], 0)


class GeographyAndProviderTests(TestCase):
    def test_segment_distances_and_inaccessible_station(self):
        from planner.geography import route_candidates
        points = [[-100, 35], [-105, 35], [-110, 35]]
        stations = [dict(latitude=35, longitude=-105, price=3), dict(latitude=40, longitude=-105, price=1)]
        candidates = route_candidates(points, stations, corridor=1, segment_miles=[300, 400])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['route_mile'], 300)

    @patch('planner.services.httpx.Client')
    def test_malformed_geocoder_is_provider_failure(self, client):
        from django.core.cache import cache
        from planner.services import locate, ProviderFailure
        cache.clear()
        client.return_value.__enter__.return_value.get.return_value.json.return_value = [{}]
        with self.assertRaises(ProviderFailure):
            locate('Unknown location fixture')

    @patch('planner.services.httpx.Client')
    def test_route_annotations_and_cache(self, client):
        from django.core.cache import cache
        from planner.services import get_route
        cache.clear()
        mocked = client.return_value.__enter__.return_value.get
        mocked.return_value.json.return_value = {'code': 'Ok', 'routes': [{'distance': 1000, 'duration': 100,
            'geometry': {'type': 'LineString', 'coordinates': [[-100, 35], [-101, 35]]},
            'legs': [{'annotation': {'distance': [1000]}}]}]}
        route, hit = get_route((35, -100), (35, -101))
        self.assertFalse(hit)
        self.assertAlmostEqual(route['segment_miles'][0], .621371192)
        self.assertTrue(get_route((35, -100), (35, -101))[1])
        self.assertEqual(mocked.call_count, 1)


class PriceImportTests(TestCase):
    def test_conflicting_prices_and_invalid_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'prices.csv'
            path.write_text('OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price\n'
                            '1,Test,123 Main,Test,AZ,1,4.25\n'
                            '1,Test,123 Main,Test,AZ,1,3.25\n'
                            '2,Other,456 Main,Test,AZ,1,NaN\n')
            call_command('import_stations', csv=str(path))
        self.assertEqual(Station.objects.count(), 1)
        self.assertEqual(float(Station.objects.get().price), 3.25)
