# VS Code installation and demonstration (Windows PowerShell)

## Prerequisites
- Python 3.13 (`py -3.13 --version`)
- VS Code with Microsoft Python extension
- Git and optional Docker Desktop
- Internet connection for pip and the OSRM route API

## Quick start (SQLite: fewest prerequisites)
1. Download ZIP and extract it, for example `C:\projects\spotter-fuel-route-api`.
2. Open VS Code > File > Open Folder > select extracted directory.
3. VS Code > Terminal > New Terminal (PowerShell).
4. Create environment: `py -3.13 -m venv .venv`
5. Activate: `.\.venv\Scripts\Activate.ps1` (if execution policy blocks it, run `.\.venv\Scripts\python.exe` directly instead of activating).
6. Install: `python -m pip install -r requirements.txt`
7. Copy `.env.example` to `.env`: `Copy-Item .env.example .env`; edit `GEOCODER_USER_AGENT` to provide contact details.
8. Prepare DB: `python manage.py migrate --noinput`
9. Import fuel CSV: `python manage.py import_stations`, then `python manage.py prepare_corridor_coordinates --apply`
10. Verify station seed count: `python manage.py shell -c "from planner.models import Station; print(Station.objects.count(),Station.objects.filter(latitude__isnull=False).count())"`
11. Start: `python manage.py runserver 127.0.0.1:8000`
12. Open `http://127.0.0.1:8000/api/docs/` and Postman.
13. Import `postman_collection.json` into Postman; run the Optimize request. Requires internet access to the OSRM demo server.
14. Stop server with Ctrl+C and run: `python -m pytest -q`.

## Docker alternative (PostgreSQL)
1. `docker compose build`
2. `docker compose up -d db`
3. `docker compose run --rm api python manage.py migrate --noinput`
4. `docker compose run --rm api python manage.py import_stations`, then `docker compose run --rm api python manage.py prepare_corridor_coordinates --apply`
5. `docker compose up -d api`
6. Open Swagger at `http://127.0.0.1:8000/api/docs/`.

## Helpful demos
- `GET http://127.0.0.1:8000/health/`
- `GET http://127.0.0.1:8000/api/v1/stations/stats/`
- `POST http://127.0.0.1:8000/api/v1/routes/optimize/`

## Troubleshooting
- `502 provider_failure`: external OSRM or Nominatim unavailable. Try the listed preset city names or explicit coordinates.
- `422 no_feasible_fuel_plan`: no reachable geolocated stations given the starting fuel, station coverage and model assumptions.
- `python not found`: run with `.\.venv\Scripts\python.exe`.
- Few fuel stations: run `python manage.py prepare_corridor_coordinates --apply`. Twelve source-reviewed stations are bundled for the demonstrated corridors; nationwide coverage remains incomplete.
- External service policies: use only modest test traffic and respect service-specific terms. Public OSRM is not production infrastructure.
