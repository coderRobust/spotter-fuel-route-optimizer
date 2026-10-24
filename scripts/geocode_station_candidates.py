import argparse
import csv
import os
import time
from pathlib import Path

import httpx

SOURCE = Path("data/us_stations_needing_geocoding.csv")
OUTPUT = Path("data/geocoding/provider_candidates.csv")

FIELDS = [
    "opis_id", "name", "address", "city", "state",
    "latitude", "longitude", "returned_address",
    "returned_city", "returned_state", "result_type",
    "confidence", "review_status",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--states", default="")
    args = parser.parse_args()

    api_key = os.environ.get("GEOAPIFY_API_KEY")
    if not api_key:
        raise SystemExit("Set GEOAPIFY_API_KEY first.")
    if not 1 <= args.limit <= 500:
        raise SystemExit("--limit must be between 1 and 500")

    allowed = {
        x.strip().upper()
        for x in args.states.split(",") if x.strip()
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if OUTPUT.exists():
        with OUTPUT.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))

    done = {
        (r["opis_id"], r["city"].casefold(), r["state"])
        for r in existing
    }

    processed = 0
    no_match = 0

    with SOURCE.open(newline="", encoding="utf-8") as source:
        rows = csv.DictReader(source)

        with httpx.Client(timeout=20) as client:
            for station in rows:
                if processed >= args.limit:
                    break

                state = station["state"].strip().upper()
                if allowed and state not in allowed:
                    continue

                key = (
                    station["opis_id"],
                    station["city"].casefold(),
                    state,
                )
                if key in done:
                    continue

                # Require a usable street/highway reference.
                if not station["address"].strip():
                    continue

                query = (
                    f'{station["name"]}, {station["address"]}, '
                    f'{station["city"]}, {state}, USA'
                )

                try:
                    response = client.get(
                        "https://api.geoapify.com/v1/geocode/search",
                        params={
                            "text": query,
                            "filter": "countrycode:us",
                            "format": "json",
                            "limit": 1,
                            "apiKey": api_key,
                        },
                    )
                    response.raise_for_status()
                    results = response.json().get("results", [])
                except (httpx.HTTPError, ValueError) as error:
                    print("Provider error; stopping:", type(error).__name__)
                    break

                result = results[0] if results else {}
                rank = result.get("rank") or {}

                record = {
                    "opis_id": station["opis_id"],
                    "name": station["name"],
                    "address": station["address"],
                    "city": station["city"],
                    "state": state,
                    "latitude": result.get("lat", ""),
                    "longitude": result.get("lon", ""),
                    "returned_address": result.get("formatted", ""),
                    "returned_city": result.get("city", ""),
                    "returned_state": result.get("state_code", ""),
                    "result_type": result.get("result_type", ""),
                    "confidence": rank.get("confidence", ""),
                    "review_status": "UNVERIFIED",
                }

                existing.append(record)
                done.add(key)
                processed += 1
                if not results:
                    no_match += 1

                print(
                    f'{processed}: {station["opis_id"]} '
                    f'{station["city"]}, {state} -> '
                    f'{record["result_type"]} '
                    f'{record["confidence"]}'
                )

                # Conservative request pacing.
                time.sleep(0.5)

    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing)

    print("\nNew queries:", processed)
    print("No matching result:", no_match)
    print("Total review rows:", len(existing))
    print("Saved:", OUTPUT)
    print("Coordinates have NOT been verified or imported.")


if __name__ == "__main__":
    main()
