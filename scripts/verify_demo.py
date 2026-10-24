"""Run the real endpoint twice and record latency/call counts without persisting keys."""
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

payload = {'start': 'Chicago, IL', 'finish': 'Los Angeles, CA',
           'vehicle': {'max_range_miles': 500, 'mpg': 10, 'starting_fuel_gallons': 50}}
cache.clear()
results = []
original = services.httpx.Client.get
for label in ('uncached', 'cached'):
    calls = []
    def counted(client, url, *args, **kwargs):
        calls.append('routing' if '/route/v1/' in url else 'geocoding')
        return original(client, url, *args, **kwargs)
    started = time.perf_counter()
    with override_settings(ALLOWED_HOSTS=['testserver']), patch.object(services.httpx.Client, 'get', counted):
        response = APIClient().post('/api/v1/routes/optimize/', payload, format='json')
    body = response.json()
    if 'route' in body:
        body['route']['geometry'] = {'omitted_from_report': True}
    results.append({'run': label, 'status': response.status_code,
                    'latency_seconds': round(time.perf_counter() - started, 3),
                    'routing_calls': calls.count('routing'), 'geocoding_calls': calls.count('geocoding'), 'response': body})
print(json.dumps({'request': payload, 'runs': results}, indent=2))
