import hashlib,json,logging,math
import httpx
from django.conf import settings
from django.core.cache import cache
from .geography import MILES_PER_KM
logger=logging.getLogger(__name__)
class ProviderFailure(Exception):pass
class PlaceNotFound(ProviderFailure):pass
class NoDrivingRoute(ProviderFailure):pass
CITY_PRESETS={
 'chicago, il':(41.8781,-87.6298),'los angeles, ca':(34.0522,-118.2437),
 'las vegas, nv':(36.1699,-115.1398),'denver, co':(39.7392,-104.9903),
 'new york, ny':(40.7128,-74.0060),'albuquerque, nm':(35.0844,-106.6504),
 'oklahoma city, ok':(35.4676,-97.5164),'amarillo, tx':(35.2220,-101.8313),
 'st louis, mo':(38.627,-90.1994),'phoenix, az':(33.4484,-112.074),
 'dallas, tx':(32.7767,-96.797),'san francisco, ca':(37.7749,-122.4194),
 'tulsa, ok':(36.154,-95.9928),'flagstaff, az':(35.1983,-111.6513),
 'indianapolis, in':(39.7684,-86.1581)
}
def locate(place,coords=None):
 if coords:return (coords['lat'],coords['lon'])
 norm=' '.join(place.lower().strip().split())
 key='geo:'+hashlib.sha256(norm.encode()).hexdigest();cached=cache.get(key)
 if cached:return cached
 if norm in CITY_PRESETS:
  result=CITY_PRESETS[norm];cache.set(key,result,86400);return result
 try:
  with httpx.Client(timeout=9,headers={'User-Agent':settings.GEOCODER_USER_AGENT}) as client:
   response=client.get(settings.GEOCODER_BASE_URL.rstrip('/')+'/search',params={'q':place+', USA','format':'json','limit':1,'countrycodes':'us'})
   response.raise_for_status()
   payload=response.json()
  if not payload:raise PlaceNotFound('US location not found')
  result=(float(payload[0]['lat']),float(payload[0]['lon']))
  if not (18<=result[0]<=72 and -180<=result[1]<=-66):raise PlaceNotFound('Location is outside supported US bounds')
  cache.set(key,result,604800);return result
 except httpx.HTTPError as error:raise ProviderFailure('Geocoder unavailable') from error
 except (ValueError, KeyError, TypeError, IndexError) as error:raise ProviderFailure('Malformed geocoder response') from error

def get_route(start,end,via=None):
 key='route:v3:'+hashlib.sha256(json.dumps([settings.ROUTING_BASE_URL,start,end,via]).encode()).hexdigest()
 saved=cache.get(key)
 if saved:return saved,True
 points=[start,*(via or []),end]
 url=settings.ROUTING_BASE_URL.rstrip('/')+'/route/v1/driving/'+';'.join(f'{p[1]},{p[0]}' for p in points)
 params={'overview':'full','geometries':'geojson','steps':'false','annotations':'distance'}
 if via:
  params.update(radiuses=';'.join(['75']*len(points)),snapping='any',continue_straight='false')
 try:
  with httpx.Client(timeout=18) as client:
   response=client.get(url,params=params)
   body=response.json()
   if response.status_code in (200,400) and body.get('code') in ('NoRoute','NoSegment'):
    raise NoDrivingRoute('No drivable route found between these endpoints')
   response.raise_for_status()
  if body.get('code') in ('NoRoute','NoSegment'):raise NoDrivingRoute('No drivable route found between these endpoints')
  if body.get('code')!='Ok' or not body.get('routes'):raise ProviderFailure('Malformed routing provider response')
  route=body['routes'][0]
  if not all(isinstance(route.get(k), (int,float)) and math.isfinite(route[k]) and route[k]>=0 for k in ('distance','duration')):
   raise ProviderFailure('Invalid routing distance or duration')
  result={'distance_miles':route['distance']/1000*MILES_PER_KM,
   'duration_minutes':round(route['duration']/60,1),'geometry':route['geometry']}
  if result['geometry'].get('type')!='LineString':raise ProviderFailure('Unsupported route geometry')
  points=result['geometry'].get('coordinates',[])
  if len(points)<2 or any(len(p)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in p) or not(-180<=p[0]<=180 and -90<=p[1]<=90) for p in points):
   raise ProviderFailure('Invalid route coordinates')
  segments=[d / 1000 * MILES_PER_KM for leg in route.get('legs', []) for d in leg.get('annotation', {}).get('distance', [])]
  if len(segments)==len(points)-1 and all(math.isfinite(d) and d>=0 for d in segments) and abs(sum(segments)-result['distance_miles'])<.01:
   result['segment_miles']=segments
  if via:
   legs=[leg['distance']/1000*MILES_PER_KM for leg in route['legs']]
   snaps=[waypoint['distance'] for waypoint in body['waypoints']]
   if len(legs)!=len(via)+1 or len(snaps)!=len(via)+2 or any(not math.isfinite(d) or d<0 for d in legs+snaps) or max(snaps)>75 or abs(sum(legs)-result['distance_miles'])>.001:
    raise ProviderFailure('Invalid station-access route distances or snaps')
   result['leg_distances_miles']=legs
   result['waypoint_snap_distances_meters']=snaps
  cache.set(key,result,settings.ROUTE_CACHE_SECONDS)
  return result,False
 except httpx.HTTPError as error:raise ProviderFailure('Routing provider unavailable') from error
 except (ValueError,KeyError,TypeError,IndexError,AttributeError) as error:raise ProviderFailure('Malformed routing provider response') from error
