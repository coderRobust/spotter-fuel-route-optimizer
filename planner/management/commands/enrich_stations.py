import csv
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.core.management.base import BaseCommand, CommandError
from planner.models import Station


CACHE = Path("data/geocoding/cache.json")
REVIEW = Path("data/geocoding/review.csv")


class Command(BaseCommand):
    help = "Prepare limited, cached geocoding suggestions for manual review."

    def add_arguments(self, parser):
        parser.add_argument("--state", required=True)
        parser.add_argument("--limit", type=int, default=5)
        parser.add_argument(
            "--fetch",
            action="store_true",
            help="Explicitly allow external geocoding calls",
        )

    def handle(self, *args, **options):
        state = options["state"].upper()
        limit = options["limit"]

        if not 1 <= limit <= 10:
            raise CommandError(
                "Limit must be between 1 and 10."
            )

        CACHE.parent.mkdir(parents=True, exist_ok=True)
        REVIEW.parent.mkdir(parents=True, exist_ok=True)

        cache = (
            json.loads(CACHE.read_text())
            if CACHE.exists()
            else {}
        )

        stations = list(
            Station.objects.filter(
                state=state,
                latitude__isnull=True,
                longitude__isnull=True,
            ).order_by("id")[:limit]
        )

        if not stations:
            self.stdout.write(
                "No unlocated stations in selected state."
            )
            return

        if options["fetch"]:
            agent = os.environ.get(
                "GEOCODER_USER_AGENT", ""
            )

            if not agent or "@" not in agent:
                raise CommandError(
                    "Set GEOCODER_USER_AGENT to your "
                    "application name and contact email."
                )

        rows = []
        last_request = 0.0

        for station in stations:
            query = (
                f"{station.name}, {station.address}, "
                f"{station.city}, {station.state}, USA"
            )

            key = query.casefold().strip()

            if key not in cache:
                if not options["fetch"]:
                    self.stdout.write(
                        f"DRY RUN: {query}"
                    )
                    continue

                wait = max(
                    0.0, 1.5 - (time.monotonic() - last_request)
                )
                time.sleep(wait)

                params = urlencode({
                    "q": query,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "countrycodes": "us",
                    "limit": 3,
                })

                url = (
                    "https://nominatim.openstreetmap.org/"
                    "search?" + params
                )

                req = Request(
                    url,
                    headers={
                        "User-Agent": agent,
                        "Accept": "application/json",
                    },
                )

                try:
                    last_request = time.monotonic()

                    with urlopen(req, timeout=20) as response:
                        results = json.loads(
                            response.read().decode("utf-8")
                        )

                except (HTTPError, URLError, TimeoutError) as exc:
                    raise CommandError(
                        f"Provider request failed: {exc}"
                    )

                cache[key] = results

                CACHE.write_text(
                    json.dumps(cache, indent=2),
                    encoding="utf-8",
                )

            for result in cache[key]:
                rows.append({
                    "station_id": station.id,
                    "opis_id": station.opis_id,
                    "station_name": station.name,
                    "city": station.city,
                    "state": station.state,
                    "latitude": result.get("lat", ""),
                    "longitude": result.get("lon", ""),
                    "matched_name": result.get(
                        "display_name", ""
                    ),
                    "category": result.get("category", ""),
                    "type": result.get("type", ""),
                    "review_status": "UNVERIFIED",
                })

        fields = [
            "station_id",
            "opis_id",
            "station_name",
            "city",
            "state",
            "latitude",
            "longitude",
            "matched_name",
            "category",
            "type",
            "review_status",
        ]

        # Preserve previous review records.
        existing = []

        if REVIEW.exists():
            with REVIEW.open(
                newline="", encoding="utf-8"
            ) as handle:
                existing = list(csv.DictReader(handle))

        existing_keys = {
            (
                row["station_id"],
                row["latitude"],
                row["longitude"],
            )
            for row in existing
        }

        for row in rows:
            key = (
                str(row["station_id"]),
                str(row["latitude"]),
                str(row["longitude"]),
            )

            if key not in existing_keys:
                existing.append(row)
                existing_keys.add(key)

        with REVIEW.open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fields
            )
            writer.writeheader()
            writer.writerows(existing)

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(stations)} stations. "
                f"New suggestions: {len(rows)}. "
                f"Review file: {REVIEW}. "
                "No database coordinates modified."
            )
        )
