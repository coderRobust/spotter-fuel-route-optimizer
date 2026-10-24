import math
from rest_framework import serializers


class FiniteFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            self.fail('invalid')
        return value


class CoordinatesSerializer(serializers.Serializer):
    # Includes Alaska and Hawaii. The bounding box alone does not prove US jurisdiction.
    lat = FiniteFloatField(min_value=18, max_value=72)
    lon = FiniteFloatField(min_value=-180, max_value=-66)


class VehicleSerializer(serializers.Serializer):
    max_range_miles = FiniteFloatField(default=500, min_value=1, max_value=1500)
    mpg = FiniteFloatField(default=10, min_value=.1, max_value=200)
    starting_fuel_gallons = FiniteFloatField(required=False, allow_null=True, min_value=0)


class OptimizeSerializer(serializers.Serializer):
    start = serializers.CharField(required=False, allow_blank=False, max_length=160)
    finish = serializers.CharField(required=False, allow_blank=False, max_length=160)
    start_coordinates = CoordinatesSerializer(required=False)
    finish_coordinates = CoordinatesSerializer(required=False)
    vehicle = VehicleSerializer(required=False)
    corridor_miles = FiniteFloatField(default=15, min_value=1, max_value=50)
    verify_road_access = serializers.BooleanField(default=True)
    allow_approximate_stations = serializers.BooleanField(default=False)

    def validate(self, attrs):
        for field in ('start', 'finish'):
            if field not in attrs and f'{field}_coordinates' not in attrs:
                raise serializers.ValidationError({field: 'Provide a US place string or coordinates.'})
        vehicle = attrs.get('vehicle', {})
        tank = vehicle.get('max_range_miles', 500) / vehicle.get('mpg', 10)
        if vehicle.get('starting_fuel_gallons') is not None and vehicle['starting_fuel_gallons'] > tank:
            raise serializers.ValidationError({'vehicle': 'Starting fuel cannot exceed tank capacity.'})
        return attrs
