import csv
from copy import deepcopy
import io
import tempfile
from pathlib import Path
from unittest import TestCase

from django.core.management import call_command
from django.test import TestCase as DjangoTestCase
from planner.models import Station

from scripts.enrich_nationwide import exact_poi


class NationwideIdentityTests(TestCase):
    def setUp(self):
        self.station = dict(opis_id='64481', name='LOVES TRAVEL STOP #282', city='Joplin', state='MO')
        self.operator = dict(A='282', B='Joplin', C='MO', D='64481')
        self.poi = {'geometry': {'type': 'Point', 'coordinates': [-94.54, 37.01]},
                    'properties': {'country_code': 'us', 'state_code': 'MO',
                                   'datasource': {'raw': {'amenity': 'fuel', 'brand': "Love's", 'ref': '282'}}}}

    def test_three_source_identity_matches(self):
        self.assertTrue(exact_poi(self.station, self.operator, self.poi))

    def test_brand_only_city_result_never_verified(self):
        poi = deepcopy(self.poi)
        del poi['properties']['datasource']['raw']['ref']
        self.assertFalse(exact_poi(self.station, self.operator, poi))

    def test_wrong_opis_store_state_or_brand_rejected(self):
        self.assertFalse(exact_poi(self.station, {**self.operator, 'D': '123'}, self.poi))
        self.assertFalse(exact_poi(self.station, {**self.operator, 'A': '999'}, self.poi))
        for change in [{'brand': 'Pilot'}, {'amenity': 'city'}, {'ref': '999'}]:
            poi = deepcopy(self.poi)
            poi['properties']['datasource']['raw'].update(change)
            self.assertFalse(exact_poi(self.station, self.operator, poi))
        poi = deepcopy(self.poi)
        poi['properties']['country_code'] = 'ca'
        self.assertFalse(exact_poi(self.station, self.operator, poi))

    def test_wrong_brand_rejected_even_with_operator_url(self):
        poi = deepcopy(self.poi)
        poi['properties']['datasource']['raw'].update(brand='Pilot', website='https://www.loves.com/locations/282')
        self.assertFalse(exact_poi(self.station, self.operator, poi))


class NationwidePreparationTests(DjangoTestCase):
    def test_bundled_matches_import_offline_and_idempotently(self):
        call_command('import_stations', stdout=io.StringIO())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'nationwide.csv'
            call_command('prepare_nationwide_coordinates', output=str(output), apply=True, stdout=io.StringIO())
            with output.open(newline='', encoding='utf-8') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 94)
            self.assertEqual(Station.objects.filter(precision='station_verified').count(), 94)

            call_command('prepare_nationwide_coordinates', output=str(output), apply=True, stdout=io.StringIO())
            self.assertEqual(Station.objects.filter(precision='station_verified').count(), 94)
