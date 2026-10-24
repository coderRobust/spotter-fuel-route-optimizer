import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/'.env')
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY','INSECURE-development-only')
DEBUG=os.environ.get('DJANGO_DEBUG','0')=='1'
ALLOWED_HOSTS=os.environ.get('DJANGO_ALLOWED_HOSTS','127.0.0.1,localhost').split(',')
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.staticfiles','rest_framework','drf_spectacular','planner']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION='config.wsgi.application'
url=os.environ.get('DATABASE_URL','sqlite:///db.sqlite3')
if url.startswith('postgres'):
 parsed=urlparse(url)
 DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':parsed.path.lstrip('/'),'USER':parsed.username,'PASSWORD':parsed.password,'HOST':parsed.hostname,'PORT':parsed.port or 5432,'CONN_MAX_AGE':60}}
else:
 DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
CACHES={'default':{'BACKEND':'django.core.cache.backends.filebased.FileBasedCache','LOCATION':os.environ.get('CACHE_LOCATION', str(BASE_DIR / '.cache' / 'fuelroute'))}}
REST_FRAMEWORK={'DEFAULT_RENDERER_CLASSES':['rest_framework.renderers.JSONRenderer','rest_framework.renderers.BrowsableAPIRenderer'],'DEFAULT_SCHEMA_CLASS':'drf_spectacular.openapi.AutoSchema','DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.AnonRateThrottle'],'DEFAULT_THROTTLE_RATES':{'anon':'30/min'}}
SPECTACULAR_SETTINGS={'TITLE':'FuelRoute Optimizer API','VERSION':'1.0.0','DESCRIPTION':'Fuel-aware USA routing assessment'}
STATIC_URL='static/'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
ROUTING_BASE_URL=os.environ.get('ROUTING_BASE_URL','https://router.project-osrm.org')
GEOCODER_BASE_URL=os.environ.get('GEOCODER_BASE_URL','https://nominatim.openstreetmap.org')
GEOCODER_USER_AGENT=os.environ.get('GEOCODER_USER_AGENT','spotter-route-assessment/1.0 (contact: change-me@example.com)')
ROUTE_CACHE_SECONDS=int(os.environ.get('ROUTE_CACHE_SECONDS','1800'))
