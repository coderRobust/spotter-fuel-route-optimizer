from .diagnostics import fuel_gap_diagnostics
from drf_spectacular.utils import extend_schema
from planner.swagger_schemas import FuelRouteRequestSchema

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count
from .models import Station
from .serializers import OptimizeSerializer
from .services import locate,get_route,ProviderFailure
from .geography import route_candidates
from .optimization import optimize_fuel_stops,UnreachableRoute
class HealthView(APIView):
 authentication_classes=[]
 def get(self,request):return Response({'status':'ok'})
class StationStatsView(APIView):
 def get(self,request):
  return Response({'stations':Station.objects.count(),'located':Station.objects.filter(latitude__isnull=False,longitude__isnull=False).count()})
class OptimizeView(APIView):
 @extend_schema(
     request=FuelRouteRequestSchema,
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
  except ProviderFailure as err:return Response({'error':'provider_failure','detail':str(err)},status=502)
  # For simplicity a bounded candidate pool is read from the DB; corridor filter is geometric.
  qs=Station.objects.filter(latitude__isnull=False,longitude__isnull=False).values('opis_id','name','city','state','latitude','longitude','price')
  stations=[{**s,'price':float(s['price'])} for s in qs.iterator()]
  candidates=route_candidates(route['geometry']['coordinates'],stations,args['corridor_miles'])
  # Projected geometry distances may differ from OSRM's reported route distance.
  # Scale every station mile marker consistently against OSRM mileage.
  from .geography import distance_miles
  coords=route['geometry']['coordinates']
  geometric=sum(distance_miles((a[1],a[0]),(b[1],b[0])) for a,b in zip(coords,coords[1:]))
  if geometric>0:
   for s in candidates:s['route_mile']=round(s['route_mile']*route['distance_miles']/geometric,3)
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
    ),
}, status=422)
  return Response({'route':route,'fuel_plan':plan,'metadata':{
   'routing_cache_hit':hit,'candidate_stations':len(candidates),'station_coordinate_precision':'city_centroid_approximation',
   'route_access':'projected proximity only; station detours are not verified',
   'cost_basis':'additional purchases only; existing starting fuel excluded',
   'notes':'Optimal purchases for the modeled fixed route and its approximate stations; not a global road-network optimum.'}})
