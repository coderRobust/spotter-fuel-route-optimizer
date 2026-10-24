"""Map rendering reuses the computed route; opening a map never calls routing."""
import secrets
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from django.http import Http404


def cache_map(route, plan):
    token = secrets.token_urlsafe(24)
    cache.set('map:' + token, {'route': {k: v for k, v in route.items() if k != 'segment_miles'}, 'fuel_plan': plan}, settings.ROUTE_CACHE_SECONDS)
    return '/maps/' + token + '/'


def route_map(request, token):
    result = cache.get('map:' + token)
    if result is None:
        raise Http404('Map expired; submit the route request again.')
    return render(request, 'planner/route_map.html', {'result': result})
