import hashlib,json,logging
import httpx
from django.conf import settings
from django.core.cache import cache
from .geography import MILES_PER_KM
logger=logging.getLogger(__name__)
class ProviderFailure(Exception):pass
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
  if not payload:raise ProviderFailure('US location not found')
  result=(float(payload[0]['lat']),float(payload[0]['lon']))
  if not (24<=result[0]<=50 and -125<=result[1]<=-66):raise ProviderFailure('Only contiguous USA is supported')
  cache.set(key,result,604800);return result
 except httpx.HTTPError as error:raise ProviderFailure('Geocoder unavailable') from error
 except (ValueError, KeyError, TypeError, IndexError) as error:raise ProviderFailure('Malformed geocoder response') from error

def get_route(start,end):
 key='route:'+hashlib.sha256(json.dumps([start,end]).encode()).hexdigest()
 saved=cache.get(key)
 if saved:return saved,True
 url=settings.ROUTING_BASE_URL.rstrip('/')+'/route/v1/driving/'+f'{start[1]},{start[0]};{end[1]},{end[0]}'
 try:
  with httpx.Client(timeout=18) as client:
   response=client.get(url,params={'overview':'full','geometries':'geojson','steps':'false','annotations':'distance'})
   response.raise_for_status()
   body=response.json()
  if body.get('code')!='Ok' or not body.get('routes'):raise ProviderFailure('No drivable route found')
  route=body['routes'][0]
  result={'distance_miles':round(route['distance']/1000*MILES_PER_KM,2),
   'duration_minutes':round(route['duration']/60,1),'geometry':route['geometry']}
  if result['geometry'].get('type')!='LineString':raise ProviderFailure('Unsupported route geometry')
  segments=[d / 1000 * MILES_PER_KM for leg in route.get('legs', []) for d in leg.get('annotation', {}).get('distance', [])]
  if len(segments)==len(result['geometry']['coordinates'])-1:
   result['segment_miles']=segments
  cache.set(key,result,settings.ROUTE_CACHE_SECONDS)
  return result,False
 except httpx.HTTPError as error:raise ProviderFailure('Routing provider unavailable') from error
 except (ValueError,KeyError,TypeError) as error:raise ProviderFailure('Malformed routing provider response') from error
