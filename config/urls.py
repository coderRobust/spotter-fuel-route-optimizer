from django.urls import path
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView
from planner.views import OptimizeView,HealthView,StationStatsView
urlpatterns=[path('health/',HealthView.as_view()),path('api/v1/routes/optimize/',OptimizeView.as_view()),path('api/v1/stations/stats/',StationStatsView.as_view()),path('api/schema/',SpectacularAPIView.as_view(),name='schema'),path('api/docs/',SpectacularSwaggerView.as_view(url_name='schema'),name='swagger-ui')]
