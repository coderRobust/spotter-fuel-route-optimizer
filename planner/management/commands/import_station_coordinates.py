import csv
import math

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from planner.station_matching import US_STATES

from planner.models import Station


class Command(BaseCommand):
    help = "Safely import trusted, verified coordinates for CSV stations."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True)
        parser.add_argument(
            "--apply", action="store_true",
            help="Write matches to database. Without this, dry-run only."
        )

    def handle(self, *args, **options):
        required = {
            "opis_id", "city", "state", "address",
            "latitude", "longitude", "provider", "provider_id", "confidence",
            "review_status", "evidence", "reviewer", "reviewed_at",
        }
        proposed = []
        rejected = []
        seen = set()
        assigned = set()

        try:
            with open(options["csv"], newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or not required.issubset(reader.fieldnames):
                    raise CommandError(
                        "CSV requires columns: " + ", ".join(sorted(required))
                    )
                for line, row in enumerate(reader, start=2):
                    try:
                        opis = row["opis_id"].strip()
                        city = row["city"].strip()
                        state = row["state"].strip().upper()
                        address = row["address"].strip()
                        lat = float(row["latitude"])
                        lon = float(row["longitude"])

                        if not all((opis, city, state, address)):
                            raise ValueError("Missing identity/address")
                        if not (math.isfinite(lat) and math.isfinite(lon)):
                            raise ValueError("Non-finite coordinates")
                        if not (24 <= lat <= 50 and -125 <= lon <= -66):
                            raise ValueError("Outside configured contiguous-US bounds")

                        if state not in US_STATES:
                            raise ValueError("Not a US station")
                        if row['review_status'] != 'VERIFIED':
                            raise ValueError("Independent verification required")
                        if not all(row[k].strip() for k in ('provider', 'provider_id', 'evidence', 'reviewer')):
                            raise ValueError("Missing provenance or independent evidence")
                        confidence = float(row['confidence'])
                        reviewed_at = parse_datetime(row['reviewed_at'])
                        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                            raise ValueError("Invalid confidence")
                        if reviewed_at is None or timezone.is_naive(reviewed_at):
                            raise ValueError("Timezone-aware review timestamp required")
                        assignment = (row['provider'], row['provider_id'])
                        coordinate = (lat, lon)
                        if assignment in assigned or coordinate in assigned:
                            raise ValueError("Duplicate provider POI or coordinate assignment")
                        assigned.update((assignment, coordinate))
                        if Station.objects.filter(latitude=lat, longitude=lon).exclude(
                            opis_id=opis, city__iexact=city, state=state
                        ).exists():
                            raise ValueError("Coordinates assigned to a different station")
                        if Station.objects.filter(coordinate_provider=row['provider'], coordinate_provider_id=row['provider_id']).exclude(
                            opis_id=opis, city__iexact=city, state=state
                        ).exists():
                            raise ValueError("Provider POI assigned to a different station")
                        key = (opis, city.casefold(), state)
                        if key in seen:
                            raise ValueError("Duplicate station identity")
                        seen.add(key)

                        station = Station.objects.filter(
                            opis_id=opis, state=state
                        ).filter(city__iexact=city).first()

                        if station is None:
                            raise ValueError("Station not found")
                        if station.address.strip().casefold() != address.casefold():
                            raise ValueError("Address does not match source CSV")
                        if station.precision == "station_verified":
                            if (station.latitude, station.longitude) != (lat, lon):
                                raise ValueError("Existing verified coordinates differ")
                            continue

                        station.latitude = lat
                        station.longitude = lon
                        station.precision = "station_verified"
                        station.coordinate_provider = row['provider']
                        station.coordinate_provider_id = row['provider_id']
                        station.coordinate_confidence = confidence
                        station.coordinate_evidence = row['evidence']
                        station.coordinate_reviewer = row['reviewer']
                        station.coordinate_reviewed_at = reviewed_at
                        proposed.append(station)
                    except (ValueError, TypeError, AttributeError) as error:
                        rejected.append((line, str(error)))
        except OSError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            f"Matched={len(proposed)} Rejected={len(rejected)} "
            f"Mode={'APPLY' if options['apply'] else 'DRY RUN'}"
        )
        for line, reason in rejected[:20]:
            self.stdout.write(f"Rejected line {line}: {reason}")

        if rejected:
            raise CommandError(
                "Import aborted: resolve rejected rows; database unchanged."
            )

        if options["apply"]:
            with transaction.atomic():
                Station.objects.bulk_update(
                    proposed, ["latitude", "longitude", "precision", "coordinate_provider", "coordinate_provider_id", "coordinate_confidence", "coordinate_evidence", "coordinate_reviewer", "coordinate_reviewed_at"],
                    batch_size=400
                )
            self.stdout.write(self.style.SUCCESS(
                f"Updated {len(proposed)} stations."
            ))
        else:
            self.stdout.write(
                "Dry run complete. Rerun with --apply after review."
            )
