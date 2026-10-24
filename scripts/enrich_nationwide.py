"""Cross-check CSV identities, official operator codes and actual OSM fuel POIs.

City geocodes are search centers only and are NEVER station coordinates.
Only exact operator/store/OPIS/state matches can pass the validator.
Provider results are checkpointed privately. No credentials enter outputs.
"""
import argparse
import asyncio
import csv
import hashlib
import io
import json
import os
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

OPERATOR_URL = 'https://edge.sitecorecloud.io/lovestravela9dd-loves2161-lovesprod042a-cf5a/media/images/bililng-station-codes/station-code-master-list-10926-excel.xlsx'


def normalized(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())


def operator_rows(content):
    namespace = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        strings = [''.join(x.itertext()) for x in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', namespace)]
        rows = []
        for row in ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('.//m:row', namespace):
            values = {}
            for cell in row:
                value = cell.find('m:v', namespace)
                if value is not None:
                    values[re.sub(r'\d', '', cell.attrib['r'])] = strings[int(value.text)] if cell.attrib.get('t') == 's' else value.text
            if all(values.get(k) for k in ('A', 'B', 'C', 'D')) and values['A'].strip().isdigit():
                rows.append({k: str(v).strip() for k, v in values.items()})
        return rows


def exact_poi(station, operator, feature):
    properties = feature.get('properties', {})
    raw = properties.get('datasource', {}).get('raw', {})
    if properties.get('country_code') != 'us' or properties.get('state_code') != station['state']:
        return False
    if raw.get('amenity') != 'fuel' or feature.get('geometry', {}).get('type') != 'Point':
        return False
    if operator['D'].lstrip('0') != station['opis_id'].lstrip('0') or operator['C'] != station['state']:
        return False
    if not re.search(r'#\s*0*' + re.escape(operator['A']) + r'\b', station['name']):
        return False
    if normalized(station['city']) not in [normalized(v) for v in operator['B'].split('/')]:
        return False
    website = urlparse(str(raw.get('website', '')))
    official_site = website.hostname in ('loves.com', 'www.loves.com')
    site_store = bool(official_site and (re.search(r'/locations/' + re.escape(operator['A']) + r'/?$', website.path)
                                       or re.search(r'-' + re.escape(operator['A']) + r'/?$', website.path)))
    brand = normalized(raw.get('brand', '') or raw.get('name', ''))
    brand_matches = brand in ('loves', 'lovestravelstop', 'lovestravelstops', 'lovestrucklanes', 'lovescountrystore')
    if raw.get('brand') and not brand_matches:
        return False
    ref_matches = str(raw.get('ref', '')).strip().lstrip('0') == operator['A'].lstrip('0')
    return site_store or (brand_matches and ref_matches)


async def run(args):
    load_dotenv('.env')
    key = os.environ.get('GEOAPIFY_API_KEY')
    if not key:
        raise SystemExit('Set GEOAPIFY_API_KEY locally; never paste it into reports.')
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=35) as client:
        book = cache / 'operator_codes.xlsx'
        if not book.exists():
            response = await client.get(args.operator_codes_url)
            response.raise_for_status()
            book.write_bytes(response.content)
        content = book.read_bytes()
        operator = {r['D'].lstrip('0'): r for r in operator_rows(content)}
        source = {}
        with open(args.csv, newline='', encoding='utf-8-sig') as handle:
            for row in csv.DictReader(handle):
                opis = row['OPIS Truckstop ID'].strip()
                if opis.lstrip('0') in operator and 'LOVE' in row['Truckstop Name'].upper():
                    source[opis] = dict(opis_id=opis, name=row['Truckstop Name'].strip(),
                                        address=row['Address'].strip(), city=row['City'].strip(), state=row['State'].strip())
        # Preserve the hand-reviewed corridor's existing exact points.
        reviewed = json.loads(Path('data/verified_corridor/manifest.json').read_text())
        skip = {r['opis_id'] for r in reviewed}
        selected = [s for s in source.values() if s['opis_id'] not in skip][:args.limit]
        semaphore = asyncio.Semaphore(3)
        request_lock = asyncio.Lock()
        next_request = 0.0
        calls = 0
        halted = False

        async def fetch(path, url, params):
            nonlocal next_request, calls, halted
            if path.exists():
                return json.loads(path.read_text())
            async with request_lock:
                if halted or calls >= args.max_requests:
                    return None
                await asyncio.sleep(max(0, next_request - time.monotonic()))
                next_request = time.monotonic() + .4
                calls += 1
            try:
                response = await client.get(url, params={**params, 'apiKey': key})
                if response.status_code in (401, 403, 429):
                    halted = True
                    print('Provider authorization/quota limit; stopping new requests.', flush=True)
                    return None
                response.raise_for_status()
                data = response.json()
                path.write_text(json.dumps(data))
                return data
            except (httpx.HTTPError, ValueError):
                return None

        async def match(station):
            async with semaphore:
                identity = station['opis_id']
                city_key = hashlib.sha256((station['city'] + '|' + station['state']).encode()).hexdigest()[:20]
                geo = await fetch(cache / ('city_' + city_key + '.json'), 'https://api.geoapify.com/v1/geocode/search',
                                  {'text': station['city'] + ', ' + station['state'] + ', USA', 'filter': 'countrycode:us', 'format': 'json', 'limit': 1})
                if not geo or not geo.get('results'):
                    return {'station': station, 'status': 'UNRESOLVED_CITY', 'matches': []}
                center = geo['results'][0]
                if center.get('country_code') != 'us':
                    return {'station': station, 'status': 'REJECTED_COUNTRY', 'matches': []}
                pois = await fetch(cache / ('pois_' + identity + '.json'), 'https://api.geoapify.com/v2/places',
                                   {'categories': 'service.vehicle.fuel', 'name': "Love's", 'filter': f"circle:{center['lon']},{center['lat']},40000", 'limit': 20})
                if not pois:
                    return {'station': station, 'status': 'PROVIDER_UNAVAILABLE', 'matches': []}
                code = operator[identity.lstrip('0')]
                matches = [f for f in pois.get('features', []) if exact_poi(station, code, f)]
                return {'station': station, 'operator_store': code['A'], 'operator_city': code['B'],
                        'status': 'EXACT_CROSS_SOURCE_MATCH' if matches else 'REVIEW_REQUIRED', 'matches': matches,
                        'candidate_count': len(pois.get('features', []))}

        results = []
        tasks = [asyncio.create_task(match(s)) for s in selected]
        for task in asyncio.as_completed(tasks):
            results.append(await task)
            if len(results) % 20 == 0:
                print(f'Processed={len(results)}/{len(selected)} exact={sum(bool(r["matches"]) for r in results)} calls={calls}', flush=True)
                output.write_text(json.dumps({'operator_url': args.operator_codes_url, 'operator_sha256': hashlib.sha256(content).hexdigest(), 'results': results}, indent=2))
        output.write_text(json.dumps({'operator_url': args.operator_codes_url, 'operator_sha256': hashlib.sha256(content).hexdigest(),
                                     'attribution': 'Geoapify; OpenStreetMap contributors, ODbL 1.0', 'requests_this_run': calls,
                                     'results': results}, indent=2))
        print(f'Completed={len(results)} exact={sum(bool(r["matches"]) for r in results)} calls={calls}; no coordinates imported.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='data/fuel-prices-for-be-assessment.csv')
    parser.add_argument('--cache', default='data/geocoding/nationwide_cache')
    parser.add_argument('--output', default='data/geocoding/nationwide_review.json')
    parser.add_argument('--operator-codes-url', default=OPERATOR_URL)
    parser.add_argument('--limit', type=int, default=600)
    parser.add_argument('--max-requests', type=int, default=1100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 600 or not 1 <= args.max_requests <= 1100:
        raise SystemExit('Limits: <=600 stations and <=1100 provider requests per run.')
    try:
        asyncio.run(run(args))
    except httpx.HTTPError:
        raise SystemExit('Operator reference unavailable; no coordinates imported.')


if __name__ == '__main__':
    main()
