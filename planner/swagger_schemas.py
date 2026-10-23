from rest_framework import serializers


class VehicleSchema(serializers.Serializer):
    max_range_miles = serializers.FloatField(
        default=500,
        min_value=1,
    )
    mpg = serializers.FloatField(
        default=10,
        min_value=0.1,
    )
    starting_fuel_gallons = serializers.FloatField(
        default=50,
        min_value=0,
    )


class FuelRouteRequestSchema(serializers.Serializer):
    start = serializers.CharField()
    finish = serializers.CharField()
    vehicle = VehicleSchema(required=False)
    corridor_miles = serializers.FloatField(
        default=15,
        required=False,
        min_value=0,
    )
