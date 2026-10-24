"""Conservative offline OSM POI matching; candidates always require human review."""
import re
from difflib import SequenceMatcher

US_STATES = frozenset('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())


def normalized(value):
    return ' '.join(re.findall(r'[a-z0-9]+', str(value).casefold()))


def match_candidate(station, feature):
    tags = feature.get('properties', {})
    geometry = feature.get('geometry', {})
    if geometry.get('type') != 'Point' or tags.get('amenity') != 'fuel':
        return None
    if station['state'] not in US_STATES:
        return None
    state = str(tags.get('addr:state', '')).removeprefix('US-').upper()
    if state != station['state'] or normalized(tags.get('addr:city', '')) != normalized(station['city']):
        return None
    name = tags.get('brand') or tags.get('name', '')
    similarity = SequenceMatcher(None, normalized(station['name']), normalized(name)).ratio()
    address = ' '.join(filter(None, [tags.get('addr:housenumber'), tags.get('addr:street')]))
    exact_address = bool(address) and normalized(address) == normalized(station['address'])
    # A highway exit alone is never an exact address match.
    street_address = bool(re.match(r'^\d+\s', address)) and not re.search(r'\b(exit|intersection)\b', address, re.I)
    lon, lat = geometry['coordinates'][:2]
    return dict(latitude=lat, longitude=lon, provider='OpenStreetMap',
                provider_id=str(feature.get('id', tags.get('@id', ''))),
                returned_name=name, returned_address=address,
                confidence=round(similarity, 3),
                review_status='REVIEW_REQUIRED' if exact_address and street_address and similarity >= .8 else 'REJECTED',
                reason='Independent identity and coordinate evidence required' if exact_address and street_address and similarity >= .8 else 'Name/address mismatch or ambiguous highway description')
