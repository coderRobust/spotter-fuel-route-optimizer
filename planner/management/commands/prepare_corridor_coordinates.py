"""Rebuild the reviewed demonstration coordinates from attributed OSM geometry."""
import csv
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from planner.models import Station


def representative_point(geometry):
    if geometry['type'] == 'Point':
        return geometry['coordinates']
    # Reviewed fuel-canopy polygons only, not generic service area/city polygons.
    ring = geometry['coordinates'][0]
    area = cx = cy = 0.0
    x0, y0 = ring[0]
    points = [(x - x0, y - y0) for x, y in ring]
    for (x, y), (xx, yy) in zip(points, points[1:]):
        cross = x * yy - xx * y
        area += cross
        cx += (x + xx) * cross
        cy += (y + yy) * cross
    if not area:
        raise CommandError('Degenerate fuel canopy polygon')
    return [x0 + cx / (3 * area), y0 + cy / (3 * area)]


def contains_point(polygon, point):
    x, y = point
    inside = False
    ring = polygon['coordinates'][0]
    for (ax, ay), (bx, by) in zip(ring, ring[1:]):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


class Command(BaseCommand):
    help = 'Generate verified coordinate CSV from the bundled, independently reviewed OSM corridor subset.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='data/verified_station_coordinates.csv')
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        directory = settings.BASE_DIR / 'data' / 'verified_corridor'
        manifest = json.loads((directory / 'manifest.json').read_text())
        geo_path = directory / 'osm_fuel_features.geojson'
        features = {f['id']: f for f in json.loads(geo_path.read_text())['features']}
        digest = hashlib.sha256(geo_path.read_bytes()).hexdigest()
        rows = []
        for review in manifest:
            station = Station.objects.filter(opis_id=review['opis_id'], state=review['state'], city__iexact=review['city']).first()
            if station is None or ('#' + review['store']) not in station.name:
                raise CommandError('Reviewed source identity missing or changed; rerun source review')
            feature = features[review['osm_id']]
            if feature['properties'].get('amenity') != 'fuel':
                raise CommandError('Reviewed OSM feature is not a fuel POI')
            lon, lat = representative_point(feature['geometry'])
            if feature['geometry']['type'] == 'Polygon' and not contains_point(feature['geometry'], (lon, lat)):
                raise CommandError('Representative point is outside the reviewed fuel footprint')
            if review['containing_site']:
                site = features[review['containing_site']]
                if (site['properties'].get('ref') != review['store']
                        or site['properties'].get('website') != review['operator_url']
                        or not contains_point(site['geometry'], (lon, lat))):
                    raise CommandError('Fuel POI does not match the reviewed operator service area')
            evidence = (f"CSV OPIS/store/city/state/highway exit cross-checked against {review['operator_url']}; "
                        f"actual fuel POI https://www.openstreetmap.org/{review['osm_id']} "
                        f"version {feature['properties']['osm_version']}; "
                        f"bundled OSM SHA256 {digest}; coordinate is "
                        + ('reviewed fuel-canopy polygon centroid' if feature['geometry']['type'] == 'Polygon' else 'fuel POI node'))
            if review['containing_site']:
                evidence += f"; within operator-matched service area https://www.openstreetmap.org/{review['containing_site']} (store ref, website and phone matched)"
            rows.append(dict(opis_id=station.opis_id, city=station.city, state=station.state, address=station.address,
                             latitude=lat, longitude=lon, provider='OpenStreetMap contributors (ODbL 1.0)',
                             provider_id=review['osm_id'], confidence=.95, review_status='VERIFIED', evidence=evidence,
                             reviewer=review['reviewer'], reviewed_at=review['reviewed_at']))
        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        call_command('import_station_coordinates', csv=str(output), apply=options['apply'], stdout=self.stdout)
