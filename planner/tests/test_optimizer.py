import unittest
from planner.optimization import optimize_fuel_stops,UnreachableRoute
class OptimizerTests(unittest.TestCase):
 def station(self,pos,price):return {'route_mile':pos,'price':price,'name':str(pos),'opis_id':str(pos)}
 def test_no_purchases_when_initial_tank_suffices(self):
  p=optimize_fuel_stops([],250,500,10)
  self.assertEqual(p['total_cost_usd'],0)
  self.assertEqual(p['total_gallons_consumed'],25)
 def test_purchase_exact_amount_at_intermediate_station(self):
  p=optimize_fuel_stops([self.station(400,3)],700,500,10)
  self.assertEqual(p['total_cost_usd'],60.0)
  self.assertAlmostEqual(p['stops'][0]['gallons'],20)
 def test_next_cheaper_station_strategy(self):
  p=optimize_fuel_stops([self.station(300,4),self.station(450,2),self.station(700,5)],900,500,10)
  self.assertEqual([x['mile_marker'] for x in p['stops']],[450.0])
  self.assertEqual(p['total_cost_usd'],80.0)
 def test_not_enough_stations(self):
  with self.assertRaises(UnreachableRoute):optimize_fuel_stops([],800,500,10)
 def test_empty_tank_purchase_at_first_station(self):
  with self.assertRaises(UnreachableRoute):optimize_fuel_stops([self.station(100,2)],200,500,10,starting_fuel=0)
 def test_bad_initial_fuel(self):
  with self.assertRaises(ValueError):optimize_fuel_stops([],50,500,10,60)
