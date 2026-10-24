import csv
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from planner.models import Station
from planner.station_matching import US_STATES, match_candidate


class Command(BaseCommand):
    help = 'Match a locally supplied OSM fuel Point GeoJSON; output review candidates, never verified coordinates.'

    def add_arguments(self, parser):
        parser.add_argument('--geojson', required=True)
        parser.add_argument('--output', required=True)
        parser.add_argument('--states', required=True, help='Comma-separated demonstration corridor states')

    def handle(self, *args, **options):
        states = set(options['states'].upper().split(','))
        if not states <= US_STATES:
            raise CommandError('Only US state codes are allowed')
        features = json.loads(Path(options['geojson']).read_text())['features']
        indexed = {}
        for feature in features:
            tags = feature.get('properties', {})
            key = (str(tags.get('addr:state', '')).removeprefix('US-').upper(), str(tags.get('addr:city', '')).casefold())
            indexed.setdefault(key, []).append(feature)
        rows = []
        for station in Station.objects.filter(state__in=states).values('opis_id', 'name', 'address', 'city', 'state'):
            for feature in indexed.get((station['state'], station['city'].casefold()), []):
                candidate = match_candidate(station, feature)
                if candidate:
                    rows.append({**station, **candidate})
        assignments = {}
        for row in rows:
            key = row['provider_id'] or (row['latitude'], row['longitude'])
            assignments[key] = assignments.get(key, 0) + 1
        for row in rows:
            if assignments[row['provider_id'] or (row['latitude'], row['longitude'])] > 1:
                row.update(review_status='REJECTED', reason='Duplicate POI assignment requires resolution')
        fields = ['opis_id', 'name', 'address', 'city', 'state', 'latitude', 'longitude', 'provider', 'provider_id', 'returned_name', 'returned_address', 'confidence', 'review_status', 'reason']
        with open(options['output'], 'w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        self.stdout.write(f'Candidates={len(rows)}; verified=0; attribution: OpenStreetMap contributors, ODbL')
