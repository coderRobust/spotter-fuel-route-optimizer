"""Validate selected station access with one additional OSRM route request.

Fuel is reoptimized on the actual road route through the selected waypoints.
This includes ramps/service roads; it does not claim optimal alternative road paths.
"""
from .optimization import optimize_fuel_stops
from .services import get_route, ProviderFailure


def verify_access_plan(start, end, candidates, initial_plan, vehicle):
    selected = initial_plan['stops']
    # OSRM's public route service has a finite waypoint budget. Never truncate a
    # plan silently or fabricate access when the route is too large.
    if len(selected) > 98:
        raise ProviderFailure('Station access route exceeds provider waypoint budget')
    via = [(s['latitude'], s['longitude']) for s in selected]
    route, hit = get_route(start, end, via=via)
    legs = route.get('leg_distances_miles', [])
    if len(legs) != len(selected) + 1:
        raise ProviderFailure('Missing road distances for station access')
    source = {(s['opis_id'], s['city'], s['state']): s for s in candidates}
    routed_stations = []
    mile = 0.0
    for index, stop in enumerate(selected):
        mile += legs[index]
        identity = (stop['opis_id'], stop['city'], stop['state'])
        if identity not in source:
            raise ProviderFailure('Access route station missing from source candidates')
        routed_stations.append({**source[identity], 'route_mile': mile})
    plan = optimize_fuel_stops(routed_stations, route['distance_miles'],
                               vehicle.get('max_range_miles', 500), vehicle.get('mpg', 10),
                               vehicle.get('starting_fuel_gallons'))
    plan['road_access_verified'] = True
    for stop in plan['stops']:
        stop['road_access_verified'] = True
    return route, plan, hit
