from rest_framework import serializers
class CoordinatesSerializer(serializers.Serializer):
 lat=serializers.FloatField(min_value=24,max_value=50)
 lon=serializers.FloatField(min_value=-125,max_value=-66)
class VehicleSerializer(serializers.Serializer):
 max_range_miles=serializers.FloatField(default=500,min_value=1,max_value=1500)
 mpg=serializers.FloatField(default=10,min_value=0.1,max_value=200)
 starting_fuel_gallons=serializers.FloatField(required=False,allow_null=True,min_value=0)
class OptimizeSerializer(serializers.Serializer):
 start=serializers.CharField(required=False,allow_blank=False,max_length=160)
 finish=serializers.CharField(required=False,allow_blank=False,max_length=160)
 start_coordinates=CoordinatesSerializer(required=False)
 finish_coordinates=CoordinatesSerializer(required=False)
 vehicle=VehicleSerializer(required=False)
 corridor_miles=serializers.FloatField(default=15,min_value=1,max_value=50)
 def validate(self,attrs):
  for field in ('start','finish'):
   if field not in attrs and f'{field}_coordinates' not in attrs:raise serializers.ValidationError({field:'Provide a place string or coordinates.'})
  vehicle=attrs.get('vehicle',{})
  tank=vehicle.get('max_range_miles',500)/vehicle.get('mpg',10)
  if vehicle.get('starting_fuel_gallons') is not None and vehicle['starting_fuel_gallons']>tank:
   raise serializers.ValidationError({'vehicle':'Starting fuel cannot exceed tank capacity.'})
  return attrs
