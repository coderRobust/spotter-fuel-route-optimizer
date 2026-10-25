"""Validate selected station access with one additional OSRM route request.

Fuel is reoptimized on the actual road route through the selected waypoints.
This includes ramps/service roads; it does not claim optimal alternative road paths.
"""
from .optimization import optimize_fuel_stops
from .services import get_route, ProviderFailure, NoDrivingRoute


def verify_access_plan(start, end, candidates, initial_plan, vehicle):
    selected = initial_plan['stops']
    # OSRM's public route service has a finite waypoint budget. Never truncate a
    # plan silently or fabricate access when the route is too large.
    if len(selected) > 98:
        raise ProviderFailure('Station access route exceeds provider waypoint budget')
    via = [(s['latitude'], s['longitude']) for s in selected]
    try:
        route, hit = get_route(start, end, via=via)
    except NoDrivingRoute as error:
        points = [dict(role='start', latitude=start[0], longitude=start[1], snap_radius_meters=None)]
        points.extend(dict(role='fuel_stop', opis_id=s['opis_id'], name=s.get('name'),
                           latitude=s['latitude'], longitude=s['longitude'], snap_radius_meters=75)
                      for s in selected)
        points.append(dict(role='finish', latitude=end[0], longitude=end[1], snap_radius_meters=None))
        index = error.waypoint_index
        error.diagnostics = {
            'provider': 'OSRM', 'provider_code': error.provider_code,
            'failed_waypoint_index': index,
            'failed_waypoint': points[index] if index is not None and 0 <= index < len(points) else None,
            'waypoints': points,
            'endpoint_snap_policy': 'OSRM default (unlimited); fuel stops limited to 75 meters',
        }
        raise
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
