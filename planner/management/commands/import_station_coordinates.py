import csv
import math

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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
            "latitude", "longitude",
        }
        proposed = []
        rejected = []
        seen = set()

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
                    proposed, ["latitude", "longitude", "precision"],
                    batch_size=400
                )
            self.stdout.write(self.style.SUCCESS(
                f"Updated {len(proposed)} stations."
            ))
        else:
            self.stdout.write(
                "Dry run complete. Rerun with --apply after review."
            )
