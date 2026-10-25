# Basemap and Chicago–Denver access regression

Verified 26 October 2026 (India). The fuel optimizer, station coordinates and 500-mile tank range were not changed.

## Basemap

The former Leaflet URL was the correct HTTPS OSM raster endpoint and included OSM attribution. However, the map response inherited Django's `Referrer-Policy: same-origin`, suppressing the browser's cross-origin Referer. That conflicts with the [OSMF tile policy](https://operations.osmfoundation.org/policies/tiles/). It is consistent with the reported block; the service's exact block classification was not determined by repeatedly requesting blocked tiles.

The map now follows the [OpenFreeMap integration guide](https://openfreemap.org/quick_start/): its Liberty vector style is rendered by pinned MapLibre GL JS 6.16.0, rather than being treated as Leaflet raster PNG tiles. The style is configurable through `BASEMAP_STYLE_URL`. OpenFreeMap, OpenMapTiles and OpenStreetMap attribution remain visible. The map response sets `strict-origin-when-cross-origin`, allowing the actual app origin while keeping the private map-token path out of cross-origin requests. No User-Agent/Referer spoofing, raster-tile proxy, cache bypass, blocked-tile retry, or tile prefetch was added.

The road geometry, blue line, start/finish markers, fuel markers/popups, zoom/pan controls, automatic bounds and purchase details use the actual API result. A failed basemap style can fall back to a plain background retaining the road/purchase data; there is no screenshot baked into the application.

Real Chrome 146 verification used a normal page load with browser caching and the real browser User-Agent. OpenFreeMap's style, metadata, sprites, fonts, background and vector tiles loaded successfully; the page showed five markers and three purchases. Marker popup interaction was checked. No JavaScript exceptions or requests to `tile.openstreetmap.org` occurred. The map response sent `Referrer-Policy: strict-origin-when-cross-origin`; the provider received `Referer: http://127.0.0.1:8012/` (the test origin, without token path).

## Road-access failure

The existing Chicago → Denver Postman request was reproduced with road-access verification enabled, the default 500-mile range, 10 MPG and 50 gallons starting fuel.

Before the fix, OSRM returned:

```json
{"code":"NoSegment","message":"Could not find a matching segment for coordinate 4"}
```

There were five waypoints, indexed from zero. Coordinate **4 was Denver**, not a fuel station. The unrestricted base route had already snapped this city-center coordinate to West 14th Avenue / West 14th Avenue Parkway / Bannock Street, **81.49919765 metres** away. The access request incorrectly applied the station-only 75-metre radius to both endpoints as well, so this otherwise drivable trip failed.

The original exact request coordinates and successful access snap distances were:

| Index | Role / identity | Latitude | Longitude | Road snap metres |
| --- | --- | ---: | ---: | ---: |
| 0 | Chicago start | 41.8781 | -87.6298 | 2.407368586 |
| 1 | OPIS 70406, Love's #754, Rochelle IL | 41.8981485 | -89.0658724 | 13.86490223 |
| 2 | OPIS 67066, Love's #361, Newton IA | 41.6804245 | -92.9975724 | 5.247248636 |
| 3 | OPIS 66236, Love's #309, Aurora NE | 40.81941033956757 | -97.9983575245021 | 4.997985659 |
| 4 | Denver finish | 39.7392 | -104.9903 | 81.49919765 |

OSRM's longitude/latitude waypoint path was:

```text
-87.6298,41.8781;-89.0658724,41.8981485;-92.9975724,41.6804245;-97.9983575245021,40.81941033956757;-104.9903,39.7392
```

The corrected radius parameter is `unlimited;75;75;75;unlimited`. OSRM's normal endpoint policy is retained for city/place inputs; each fuel point is still strictly constrained to 75 metres and checked in the response. Every fuel snap in this reproduction is under 14 metres. The provider evidence identifies an endpoint-policy bug, not an inaccessible station, incorrect carriageway or fabricated station location.

The route cache version was changed so older policy-dependent results cannot be reused. Genuine OSRM failures retain HTTP 422 and now report the provider code, failed coordinate index when available, waypoint role/OPIS/name/coordinates, submitted waypoints and snap policy. Missing road access is never silently downgraded to projected proximity. Provider outages remain 502.

After the fix the exact Postman input returned **HTTP 200**, `road_access_verified=true`, **1,009.1144 miles**, three purchases, **50.911 gallons purchased**, and **$171.64 additional fuel cost**. Routed legs were 79.9402, 218.9647, 291.9973 and 418.2121 miles, all below 500. Fuel quantities were recomputed from those road distances by the unchanged optimizer. Station locations were not edited.

## Regression checks

- Map provider, attribution, safe route JSON and map-specific Referrer-Policy.
- Configurable vector style; no former OSM raster tile endpoint in the page.
- A destination snap of 81.5 metres is accepted while the fuel station is within 75 metres.
- Fuel station snaps beyond 75 metres are still rejected.
- OSRM `NoSegment` preserves its code and zero-based waypoint index.
- An inaccessible station still returns 422 with the correct station identity and diagnostics.
- Django system check: no issues. Full suite: **54 passed**. Migration drift: none.

Only the requested fix files were committed; unrelated local documentation and demo-response edits were preserved.
