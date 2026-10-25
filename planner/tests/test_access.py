from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from planner.access import verify_access_plan
from planner.optimization import UnreachableRoute
from planner.models import Station
from planner.services import ProviderFailure


class RoadAccessTests(TestCase):
    def setUp(self):
        self.candidates = [dict(opis_id=str(i), city='Test', state='NM', name='Synthetic verified fuel',
                                latitude=35, longitude=lon, price=price, route_mile=mile)
                           for i, lon, price, mile in [(1, -104, 3, 400), (2, -108, 4, 800)]]
        self.initial = {'stops': self.candidates}
        self.access_route = {'distance_miles': 1260, 'duration_minutes': 1200,
                             'geometry': {'type': 'LineString', 'coordinates': [[-100, 35], [-104, 35], [-108, 35], [-112, 35]]},
                             'leg_distances_miles': [410, 430, 420],
                             'waypoint_snap_distances_meters': [0, 10, 20, 0]}

    @patch('planner.access.get_route')
    def test_detour_fuel_included(self, provider):
        provider.return_value = (self.access_route, False)
        route, plan, hit = verify_access_plan((35, -100), (35, -112), self.candidates, self.initial, {})
        self.assertEqual(plan['total_gallons_consumed'], 126)
        self.assertEqual(plan['total_gallons_purchased'], 76)
        self.assertEqual(plan['total_cost_usd'], 263)
        self.assertEqual([s['mile_marker'] for s in plan['stops']], [410, 840])
        self.assertTrue(all(s['road_access_verified'] for s in plan['stops']))
        self.assertEqual(provider.call_count, 1)

    @patch('planner.access.get_route')
    def test_detour_makes_first_stop_unreachable(self, provider):
        provider.return_value = ({**self.access_route, 'distance_miles': 1360,
                                  'leg_distances_miles': [510, 430, 420]}, False)
        with self.assertRaises(UnreachableRoute):
            verify_access_plan((35, -100), (35, -112), self.candidates, self.initial, {})

    @patch('planner.access.get_route')
    def test_missing_access_legs_never_fall_back_to_proximity(self, provider):
        provider.return_value = ({**self.access_route, 'leg_distances_miles': []}, False)
        with self.assertRaises(ProviderFailure):
            verify_access_plan((35, -100), (35, -112), self.candidates, self.initial, {})

    @patch('planner.access.get_route')
    @patch('planner.views.get_route')
    def test_default_api_routes_real_access(self, base, access):
        base.return_value = ({'distance_miles': 1200, 'geometry': self.access_route['geometry']}, False)
        access.return_value = (self.access_route, False)
        for c in self.candidates:
            Station.objects.create(**{k: v for k, v in c.items() if k != 'route_mile'},
                                   precision='station_verified', coordinate_evidence='Synthetic independently verified fixture')
        response = APIClient().post('/api/v1/routes/optimize/', {
            'start_coordinates': {'lat': 35, 'lon': -100}, 'finish_coordinates': {'lat': 35, 'lon': -112}}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['metadata']['road_access_verified'])
        self.assertEqual(response.data['metadata']['routing_requests'], 2)
        self.assertEqual(response.data['fuel_plan']['total_gallons_purchased'], 76)
        self.assertEqual(base.call_count + access.call_count, 2)

    @patch('planner.services.httpx.Client')
    def test_access_provider_rejects_distant_snap(self, client):
        from django.core.cache import cache
        from planner.services import get_route
        cache.clear()
        body = {'code': 'Ok', 'routes': [{'distance': 2000, 'duration': 200,
                'geometry': {'type': 'LineString', 'coordinates': [[-100, 35], [-101, 35], [-102, 35]]},
                'legs': [{'distance': 1000}, {'distance': 1000}]}],
                'waypoints': [{'distance': 0}, {'distance': 100}, {'distance': 0}]}
        client.return_value.__enter__.return_value.get.return_value.json.return_value = body
        with self.assertRaises(ProviderFailure):
            get_route((35, -100), (35, -102), via=[(35, -101)])

    @patch('planner.services.httpx.Client')
    def test_city_center_endpoint_beyond_station_radius_is_allowed(self, client):
        from django.core.cache import cache
        from planner.services import get_route
        cache.clear()
        # Denver's city-center endpoint is 81.5m from its road snap. The fuel
        # stop remains only 20m from its service road; the 75m limit applies there.
        provider = client.return_value.__enter__.return_value.get
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {'code': 'Ok', 'routes': [{
            'distance': 2000, 'duration': 200,
            'geometry': {'type': 'LineString', 'coordinates': [[-100, 35], [-101, 35], [-102, 35]]},
            'legs': [{'distance': 1000}, {'distance': 1000}]}],
            'waypoints': [{'distance': 0}, {'distance': 20}, {'distance': 81.49919765}]}
        route, _ = get_route((35, -100), (35, -102), via=[(35, -101)])
        self.assertEqual(provider.call_args.kwargs['params']['radiuses'], 'unlimited;75;unlimited')
        self.assertGreater(route['waypoint_snap_distances_meters'][-1], 75)
        self.assertLess(route['waypoint_snap_distances_meters'][1], 75)

    @patch('planner.services.httpx.Client')
    def test_no_segment_retains_provider_code_and_waypoint_index(self, client):
        from django.core.cache import cache
        from planner.services import get_route, NoDrivingRoute
        cache.clear()
        provider = client.return_value.__enter__.return_value.get
        provider.return_value.status_code = 400
        provider.return_value.json.return_value = {'code': 'NoSegment', 'message': 'Could not find a matching segment for coordinate 1'}
        with self.assertRaises(NoDrivingRoute) as caught:
            get_route((35, -100), (35, -102), via=[(35, -101)])
        self.assertEqual(caught.exception.provider_code, 'NoSegment')
        self.assertEqual(caught.exception.waypoint_index, 1)

    @patch('planner.access.get_route')
    @patch('planner.views.get_route')
    def test_inaccessible_fuel_stop_keeps_422_with_identity_diagnostics(self, base, access):
        from planner.services import NoDrivingRoute
        base.return_value = ({'distance_miles': 1200, 'geometry': self.access_route['geometry']}, False)
        access.side_effect = NoDrivingRoute('Could not find a matching segment for coordinate 1', provider_code='NoSegment', waypoint_index=1)
        for candidate in self.candidates:
            Station.objects.create(**{k: v for k, v in candidate.items() if k != 'route_mile'}, precision='station_verified', coordinate_evidence='Synthetic verified fixture')
        response = APIClient().post('/api/v1/routes/optimize/', {
            'start_coordinates': {'lat': 35, 'lon': -100}, 'finish_coordinates': {'lat': 35, 'lon': -112}}, format='json')
        self.assertEqual(response.status_code, 422)
        diagnostics = response.data['diagnostics']
        self.assertEqual(diagnostics['provider_code'], 'NoSegment')
        self.assertEqual(diagnostics['failed_waypoint']['role'], 'fuel_stop')
        self.assertEqual(diagnostics['failed_waypoint']['opis_id'], '1')
        self.assertEqual(diagnostics['failed_waypoint']['snap_radius_meters'], 75)
