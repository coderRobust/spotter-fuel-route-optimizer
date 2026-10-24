import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from planner.models import Station


class Command(BaseCommand):
    help = "Import fuel prices with bulk upserts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default="data/fuel-prices-for-be-assessment.csv",
        )
        parser.add_argument(
            "--city-locations",
            default="data/city_centroids.json",
        )

    def handle(self, *args, **opts):
        coords = json.loads(
            Path(opts["city_locations"]).read_text()
        )

        unique = {}
        read = 0
        invalid = 0
        duplicate_rows = 0
        conflicting_prices = 0

        with open(
            opts["csv"], newline="", encoding="utf-8-sig"
        ) as handle:
            for row in csv.DictReader(handle):
                read += 1
                try:
                    price = Decimal(
                        row["Retail Price"].strip()
                    )

                    if not price.is_finite() or price <= 0:
                        raise ValueError("Invalid price")

                    opis = row["OPIS Truckstop ID"].strip()
                    city = " ".join(
                        row["City"].strip().split()
                    )
                    state = row["State"].strip().upper()

                    if not opis or not city or len(state) != 2:
                        raise ValueError("Invalid station")

                    key = (opis, city.casefold(), state)

                    if key in unique:
                        duplicate_rows += 1
                        conflicting_prices += price != unique[key]["price"]

                    if (
                        key not in unique
                        or price < unique[key]["price"]
                    ):
                        unique[key] = {
                            "opis_id": opis,
                            "name": row[
                                "Truckstop Name"
                            ].strip()[:255],
                            "address": row[
                                "Address"
                            ].strip()[:255],
                            "city": city,
                            "state": state,
                            "rack_id": row[
                                "Rack ID"
                            ].strip(),
                            "price": price,
                        }

                except (
                    InvalidOperation, KeyError, ValueError
                ):
                    invalid += 1

        # Preserve previously saved coordinates.
        existing = {
            (
                s.opis_id,
                s.city.casefold(),
                s.state.upper(),
            ): s
            for s in Station.objects.all().iterator()
        }

        objects = []
        located = 0

        for key, rec in unique.items():
            old = existing.get(key)

            if old is not None and old.precision == "station_verified" and (old.address != rec["address"] or old.name != rec["name"]):
                raise CommandError("Verified station identity changed; review coordinates before reimport")

            # Prefer coordinates already stored in DB.
            if (
                old is not None
                and old.latitude is not None
                and old.longitude is not None
            ):
                lat = old.latitude
                lon = old.longitude
                precision = old.precision
            else:
                lookup = (
                    f"{rec['city'].casefold()}|"
                    f"{rec['state'].casefold()}"
                )
                location = coords.get(lookup)

                if location:
                    lat, lon = location
                    precision = "city_centroid"
                else:
                    lat = lon = None
                    precision = "unknown"

            if lat is not None and lon is not None:
                located += 1

            objects.append(Station(
                **rec,
                latitude=lat,
                longitude=lon,
                precision=precision,
            ))

        # SQLite-compatible batched upsert.
        fields = [
            "name", "address", "rack_id", "price",
            "latitude", "longitude", "precision",
        ]

        with transaction.atomic():
            Station.objects.bulk_create(
                objects,
                batch_size=400,
                update_conflicts=True,
                unique_fields=[
                    "opis_id", "city", "state"
                ],
                update_fields=fields,
            )

        self.stdout.write(self.style.SUCCESS(
            f"rows={read} "
            f"unique_station_keys={len(objects)} "
            f"bad_rows={invalid} duplicate_rows={duplicate_rows} conflicting_prices={conflicting_prices} "
            f"located={located}"
        ))
