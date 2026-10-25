from django.test import TestCase, override_settings
from planner.maps import cache_map


class MapProviderTests(TestCase):
    def test_vector_provider_and_referrer_policy_preserve_route_payload(self):
        route = {'distance_miles': 700, 'geometry': {'type': 'LineString', 'coordinates': [[-100, 35], [-110, 35]]}}
        plan = {'stops': [{'name': '</script><script>alert(1)</script>', 'latitude': 35, 'longitude': -105}], 'total_cost_usd': 30}
        path = cache_map(route, plan)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Referrer-Policy'], 'strict-origin-when-cross-origin')
        self.assertContains(response, 'https://tiles.openfreemap.org/styles/liberty')
        self.assertContains(response, 'maplibre-gl@6.16.0')
        self.assertContains(response, 'OpenMapTiles')
        self.assertContains(response, 'https://www.openstreetmap.org/copyright')
        self.assertContains(response, 'fuel-route')
        self.assertContains(response, 'setPopup')
        self.assertNotContains(response, 'tile.openstreetmap.org')
        self.assertNotContains(response, '</script><script>alert(1)</script>')
        self.assertContains(response, 'route-data')

    @override_settings(BASEMAP_STYLE_URL='https://example.test/style.json')
    def test_provider_style_is_configurable(self):
        path = cache_map({'geometry': {'type': 'LineString', 'coordinates': [[0, 0], [1, 1]]}}, {'stops': []})
        self.assertContains(self.client.get(path), 'https://example.test/style.json')
