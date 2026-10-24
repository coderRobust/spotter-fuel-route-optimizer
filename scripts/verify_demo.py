"""Exercise the real endpoint and record latency, call counts and fuel invariants."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient
from planner import services
from planner.models import Station


def audit_plan(body, starting_fuel=50, mpg=10, capacity=50):
    """Independent response-level feasibility/cost check, allowing display rounding."""
    fuel, mile, bought, cost = starting_fuel, 0, 0, 0
    for stop in body['fuel_plan']['stops']:
        if stop['mile_marker'] < mile:
            raise AssertionError('Stops are not in route order')
        fuel -= (stop['mile_marker'] - mile) / mpg
        if fuel < -.003:
            raise AssertionError('Unreachable fuel stop')
        fuel += stop['gallons']
        if fuel > capacity + .003:
            raise AssertionError('Tank capacity exceeded')
        station = Station.objects.get(opis_id=stop['opis_id'], city=stop['city'], state=stop['state'])
        if station.precision != 'station_verified' or not station.coordinate_evidence:
            raise AssertionError('Stop lacks independent location evidence')
        if abs(float(station.price) - stop['price_per_gallon_usd']) > .000001:
            raise AssertionError('Price differs from imported source CSV')
        bought += stop['gallons']
        cost += stop['gallons'] * stop['price_per_gallon_usd']
        mile = stop['mile_marker']
    fuel -= (body['route']['distance_miles'] - mile) / mpg
    plan = body['fuel_plan']
    if fuel < -.003 or abs(fuel - plan['final_fuel_gallons']) > .005:
        raise AssertionError('Invalid arrival fuel')
    if abs(bought - plan['total_gallons_purchased']) > .001 * max(1, len(plan['stops'])):
        raise AssertionError('Purchase total mismatch')
    if abs(cost - plan['total_cost_usd']) > .01 + .003 * len(plan['stops']):
        raise AssertionError('Purchase cost mismatch')
    if abs(starting_fuel + plan['total_gallons_purchased'] - plan['total_gallons_consumed'] - plan['final_fuel_gallons']) > .003:
        raise AssertionError('Fuel mass balance mismatch')
    return 'passed: station identity, source price, stop order, range, tank capacity, fuel balance and cost'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='Chicago, IL')
    parser.add_argument('--finish', default='Los Angeles, CA')
    parser.add_argument('--require-success', action='store_true')
    args = parser.parse_args()
    payload = {'start': args.start, 'finish': args.finish,
               'vehicle': {'max_range_miles': 500, 'mpg': 10, 'starting_fuel_gallons': 50}}
    cache.clear()
    results = []
    original = services.httpx.Client.get
    for label in ('uncached', 'cached'):
        calls = []
        def counted(client, url, *a, **kw):
            calls.append('routing' if '/route/v1/' in url else 'geocoding')
            return original(client, url, *a, **kw)
        started = time.perf_counter()
        with override_settings(ALLOWED_HOSTS=['testserver']), patch.object(services.httpx.Client, 'get', counted):
            response = APIClient().post('/api/v1/routes/optimize/', payload, format='json')
        elapsed = time.perf_counter() - started
        body = response.json()
        response_bytes = len(response.content)
        if response.status_code == 200:
            audit = audit_plan(body)
            body['route']['geometry'] = {'omitted_from_report': True}
        else:
            audit = 'not applicable: unsuccessful response'
        results.append({'run': label, 'status': response.status_code, 'latency_seconds': round(elapsed, 3),
                        'response_bytes': response_bytes, 'routing_calls': calls.count('routing'),
                        'geocoding_calls': calls.count('geocoding'), 'fuel_audit': audit, 'response': body})
    print(json.dumps({'request': payload, 'runs': results}, indent=2))
    if args.require_success and any(r['status'] != 200 for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
