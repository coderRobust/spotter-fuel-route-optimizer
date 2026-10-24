"""Fuel purchase optimizer for a fixed ordered route with zero-cost access to on-route stations.
Potential route-access detours are deliberately outside this optimization model.
"""
from decimal import Decimal,ROUND_HALF_UP
class UnreachableRoute(Exception):pass
def optimize_fuel_stops(stations,distance_miles,max_range=500,mpg=10,starting_fuel=None):
 """Greedy optimal fuel purchases under constant consumption, known forward station prices,
 full tank range, continuous purchases, and no cost for optional detours.
 At each stop, purchase to reach first strictly cheaper reachable stop; otherwise fill
 to capacity or only as much as needed for finish. Initial tank is free/paid previously.
 """
 if distance_miles<0 or max_range<=0 or mpg<=0:raise ValueError('Invalid distance or vehicle')
 capacity=Decimal(str(max_range))/Decimal(str(mpg))
 fuel=capacity if starting_fuel is None else Decimal(str(starting_fuel))
 if fuel<0 or fuel>capacity:raise ValueError('Invalid starting fuel')
 consumption=Decimal(str(mpg))
 nodes=[{'route_mile':Decimal('0'),'price':Decimal('0'),'origin':True}]
 for st in sorted(stations,key=lambda x:(x['route_mile'],x['price'])):
  pos=Decimal(str(st['route_mile']))
  if 0<=pos<Decimal(str(distance_miles)):
   nodes.append({**st,'route_mile':pos,'price':Decimal(str(st['price']))})
 # equal-location stations cannot be assumed as distinct purchases; keep the cheapest
 dedup=[nodes[0]]
 for node in nodes[1:]:
  if node['route_mile']==dedup[-1]['route_mile'] and not dedup[-1].get('origin'):
   if node['price']<dedup[-1]['price']:dedup[-1]=node
  else:dedup.append(node)
 nodes=dedup+[{'route_mile':Decimal(str(distance_miles)),'destination':True}]
 max_distance=Decimal(str(max_range)); stops=[];cost=Decimal('0');used=Decimal('0');bought=Decimal('0')
 for i,node in enumerate(nodes[:-1]):
  if i:
   delta=node['route_mile']-nodes[i-1]['route_mile']
   required=delta/consumption
   if fuel+Decimal('0.000001')<required:raise UnreachableRoute('Insufficient fuel to reach next station')
   fuel=max(Decimal(0),fuel-required);used+=required
  if node.get('origin'):continue
  cheaper=None
  for future in nodes[i+1:]:
   delta=future['route_mile']-node['route_mile']
   if delta>max_distance:break
   if future.get('destination') or future['price']<node['price']:
    cheaper=future;break
  target=(cheaper['route_mile']-node['route_mile'])/consumption if cheaper else capacity
  target=min(capacity,target,(nodes[-1]['route_mile']-node['route_mile'])/consumption)
  purchased=max(Decimal(0),target-fuel)
  if purchased>0:
   expense=purchased*node['price'];cost+=expense;fuel+=purchased;bought+=purchased
   stops.append({'opis_id':node.get('opis_id'),'name':node.get('name'),'city':node.get('city'),'state':node.get('state'),
    'latitude':node.get('latitude'),'longitude':node.get('longitude'),'mile_marker':round(float(node['route_mile']),2),
    'coordinate_precision':node.get('precision'),'coordinate_provider':node.get('coordinate_provider'),'coordinate_provider_id':node.get('coordinate_provider_id'),
    'arrival_fuel_gallons':round(float(fuel-purchased),3),'departure_fuel_gallons':round(float(fuel),3),
    'offset_miles':node.get('offset_miles'), 'price_per_gallon_usd':float(node['price']),
    'gallons':float(purchased.quantize(Decimal('0.001'),rounding=ROUND_HALF_UP)),
    'cost_usd':float(expense.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))})
 final_leg=(nodes[-1]['route_mile']-nodes[-2]['route_mile'])/consumption
 if fuel+Decimal('0.000001')<final_leg:raise UnreachableRoute('Insufficient fuel to reach destination')
 used+=final_leg
 return {'stops':stops,'total_gallons_purchased':float(bought.quantize(Decimal('0.001'),rounding=ROUND_HALF_UP)),
  'total_gallons_consumed':round(float(used),3),
  'total_cost_usd':float(cost.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)),
  'final_fuel_gallons':round(float(max(Decimal(0),fuel-final_leg)),3)}
