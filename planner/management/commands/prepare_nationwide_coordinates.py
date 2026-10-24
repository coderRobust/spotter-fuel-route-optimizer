"""Reproduce independently cross-validated station coordinates without API calls."""
import csv
import json
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from planner.models import Station
from scripts.enrich_nationwide import exact_poi


class Command(BaseCommand):
    help = 'Validate bundled CSV/operator/OSM identity matches and import through the standard coordinate importer.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='data/geocoding/nationwide_verified.csv')
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        path = settings.BASE_DIR / 'data' / 'nationwide' / 'validated_matches.json'
        dataset = json.loads(path.read_text())
        rows = []
        for entry in dataset['matches']:
            identity = entry['station']
            station = Station.objects.filter(opis_id=identity['opis_id'], city=identity['city'], state=identity['state']).first()
            operator = entry['operator_reference']
            if (station is None or station.address != identity['address']
                    or 'LOVE' not in station.name.upper()
                    or not exact_poi(identity, operator, entry['feature'])
                    or not exact_poi(
                        {'opis_id': station.opis_id, 'name': station.name, 'city': station.city, 'state': station.state},
                        operator, entry['feature'])):
                raise CommandError('Source identity changed; independent revalidation required')
            properties = entry['feature']['properties']
            raw = properties['datasource']['raw']
            lon, lat = entry['feature']['geometry']['coordinates']
            provider_id = {'n': 'node', 'w': 'way', 'r': 'relation'}[raw['osm_type']] + '/' + str(raw['osm_id'])
            evidence = (f"Independent supplied CSV OPIS/store/city/state identity agrees with official operator billing reference "
                        f"{dataset['operator_url']} (SHA256 {dataset['operator_sha256']}); exact OSM fuel POI operator/store "
                        f"website or ref matches https://www.openstreetmap.org/{provider_id}; "
                        "US country/state checked. City geocode used solely as search center, never as station coordinates. "
                        "Automated cross-source identity validation, not a field visit.")
            rows.append(dict(opis_id=station.opis_id, city=station.city, state=station.state, address=station.address,
                             latitude=lat, longitude=lon, provider='Geoapify / OpenStreetMap contributors (ODbL 1.0)',
                             provider_id=provider_id, confidence=.95, review_status='VERIFIED', evidence=evidence,
                             reviewer='cross-source-validator-v1', reviewed_at=dataset['validated_at']))
        if not rows:
            raise CommandError('No independently validated matches bundled')
        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        call_command('import_station_coordinates', csv=str(output), apply=options['apply'], stdout=self.stdout)
