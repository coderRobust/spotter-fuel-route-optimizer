from .diagnostics import fuel_gap_diagnostics
from drf_spectacular.utils import extend_schema

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count
from .models import Station
from .station_matching import US_STATES
from .serializers import OptimizeSerializer
from .services import locate,get_route,ProviderFailure,PlaceNotFound,NoDrivingRoute
from .geography import route_candidates
from .optimization import optimize_fuel_stops,UnreachableRoute
class HealthView(APIView):
 authentication_classes=[]
 def get(self,request):return Response({'status':'ok'})
class StationStatsView(APIView):
 def get(self,request):
  return Response({'stations':Station.objects.count(),'located':Station.objects.filter(latitude__isnull=False,longitude__isnull=False).count(),'independently_reviewed':Station.objects.filter(precision='station_verified').exclude(coordinate_evidence='').count(),'us_stations':Station.objects.filter(state__in=US_STATES).count()})
class OptimizeView(APIView):
 @extend_schema(
     request=OptimizeSerializer,
     responses={200: dict},
 )
 def post(self,request):
  validator=OptimizeSerializer(data=request.data)
  validator.is_valid(raise_exception=True)
  args=validator.validated_data
  try:
   start=locate(args.get('start'),args.get('start_coordinates'))
   end=locate(args.get('finish'),args.get('finish_coordinates'))
   route,hit=get_route(start,end)
  except PlaceNotFound as err:return Response({'error':'invalid_location','detail':str(err)},status=400)
  except NoDrivingRoute as err:return Response({'error':'no_driving_route','detail':str(err)},status=422)
  except ProviderFailure as err:return Response({'error':'provider_failure','detail':str(err)},status=502)
  # Filter indexed coordinates before projecting onto route segments.
  from math import cos, radians
  coords=route['geometry']['coordinates']
  margin_lat=args['corridor_miles']/69
  max_lat=max(abs(c[1]) for c in coords)
  margin_lon=margin_lat/max(.01,cos(radians(min(85,max_lat))))
  qs=Station.objects.filter(state__in=US_STATES,latitude__range=(min(c[1] for c in coords)-margin_lat,max(c[1] for c in coords)+margin_lat),longitude__range=(min(c[0] for c in coords)-margin_lon,max(c[0] for c in coords)+margin_lon))
  if not args['allow_approximate_stations']:
   qs=qs.filter(precision='station_verified').exclude(coordinate_evidence='')
  qs=qs.values('opis_id','name','city','state','latitude','longitude','price','precision','coordinate_provider','coordinate_provider_id')
  stations=[{**s,'price':float(s['price'])} for s in qs.iterator()]
  candidates=route_candidates(route['geometry']['coordinates'],stations,args['corridor_miles'],segment_miles=route.get('segment_miles'))
  # Projected geometry distances may differ from OSRM's reported route distance.
  # Scale every station mile marker consistently against OSRM mileage.
  from .geography import distance_miles
  coords=route['geometry']['coordinates']
  geometric=sum(distance_miles((a[1],a[0]),(b[1],b[0])) for a,b in zip(coords,coords[1:]))
  if geometric>0 and not route.get('segment_miles'):
   for s in candidates:s['route_mile']=s['route_mile']*route['distance_miles']/geometric
  vehicle=args.get('vehicle',{})
  try:
   plan=optimize_fuel_stops(candidates,route['distance_miles'],vehicle.get('max_range_miles',500),vehicle.get('mpg',10),vehicle.get('starting_fuel_gallons'))
  except UnreachableRoute as err:
   return Response({
    'error': 'no_feasible_fuel_plan',
    'detail': str(err),
    'candidate_stations': len(candidates),
    'route_distance_miles': route['distance_miles'],
    'diagnostics': fuel_gap_diagnostics(
        candidates,
        route['distance_miles'],
        vehicle.get('max_range_miles', 500),
        vehicle.get('mpg', 10),
        vehicle.get('starting_fuel_gallons'),
    ),
}, status=422)
  routing_requests=int(not hit)
  road_access_verified=False
  if args['verify_road_access'] and plan['stops']:
   from .access import verify_access_plan
   try:
    route,plan,access_hit=verify_access_plan(start,end,candidates,plan,vehicle)
    routing_requests+=int(not access_hit)
    hit=hit and access_hit
    road_access_verified=True
   except NoDrivingRoute as err:return Response({'error':'station_access_unavailable','detail':str(err)},status=422)
   except UnreachableRoute as err:return Response({'error':'no_feasible_access_fuel_plan','detail':str(err)},status=422)
   except ProviderFailure as err:return Response({'error':'provider_failure','detail':str(err)},status=502)
  from .maps import cache_map
  map_url=cache_map(route,plan)
  return Response({'map_url':map_url,'route':{k:v for k,v in route.items() if k != 'segment_miles'},'fuel_plan':plan,'metadata':{
   'routing_cache_hit':hit,'routing_requests':routing_requests,'road_access_verified':road_access_verified,'candidate_stations':len(candidates),'station_coordinate_precision':'verified only' if not args['allow_approximate_stations'] else 'mixed; see candidate_precision_counts','candidate_precision_counts':{p:sum(1 for s in candidates if s.get('precision')==p) for p in sorted({s.get('precision','unknown') for s in candidates})},
   'approximate_stations_allowed':args['allow_approximate_stations'],
   'station_distance_basis':'actual road-route leg distances' if road_access_verified else ('routing segment annotations' if route.get('segment_miles') else 'globally scaled geometry approximation'),
   'route_access':'Road-routed via selected stations; detour consumption included; road snap within 75 meters' if road_access_verified else 'Projected proximity only; station detours are not verified',
   'price_source':'data/fuel-prices-for-be-assessment.csv; minimum recorded price per OPIS/city/state; historical, no freshness guarantee',
   'coordinate_attribution':'OpenStreetMap contributors, ODbL 1.0 (bundled reviewed dataset); see stop provider fields',
   'cost_basis':'additional purchases only; existing starting fuel excluded',
   'notes':'Minimum additional purchase cost on the returned fixed route at the available fuel stops. Initial stop selection uses the base route; alternative stop combinations after road-access rerouting are not exhaustively searched.'}})
